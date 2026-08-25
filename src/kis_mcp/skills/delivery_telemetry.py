from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from time import perf_counter_ns
from urllib.parse import parse_qs, urlsplit

from fastmcp import FastMCP
from fastmcp.resources.base import ResourceResult
from fastmcp.server.middleware import Middleware, MiddlewareContext

from .catalogue import SkillCatalogue
from .errors import SkillsError
from .telemetry import SkillTelemetryEvent, SkillTelemetryStore

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class _SkillResourceIdentity:
    skill_id: str | None
    relative_path: str | None
    resource_class: str
    event_name: str


def _duration_ms(started_ns: int) -> int:
    return max(0, (perf_counter_ns() - started_ns) // 1_000_000)


def _classify(relative_path: str) -> str:
    if relative_path == "SKILL.md":
        return "SKILL.md"
    root = relative_path.split("/", 1)[0].casefold()
    if root in {"reference", "references"}:
        return "reference"
    if root in {"script", "scripts"}:
        return "script"
    if root in {"asset", "assets"}:
        return "asset"
    if root in {"agent", "agents"}:
        return "agent"
    return "other"


def _identity(uri: str) -> _SkillResourceIdentity | None:
    parsed = urlsplit(uri)
    if parsed.scheme != "skill":
        return None
    if parsed.path in {"", "/"}:
        return _SkillResourceIdentity(None, None, "catalogue", "skill_catalogue_exposed")
    parts = [part for part in parsed.path.split("/") if part]
    if parts == ["catalogue"]:
        return _SkillResourceIdentity(None, None, "catalogue", "skill_catalogue_exposed")
    if len(parts) == 2 and parts[1] == "SKILL.md":
        return _SkillResourceIdentity(parts[0], "SKILL.md", "SKILL.md", "skill_loaded")
    if len(parts) == 2 and parts[1] == "resource":
        values = parse_qs(parsed.query, keep_blank_values=True).get("path", [])
        if len(values) == 1 and values[0]:
            relative_path = values[0]
            return _SkillResourceIdentity(
                parts[0], relative_path, _classify(relative_path), "skill_resource_read"
            )
    return None


def _request_correlation(context: MiddlewareContext) -> tuple[str | None, str | None, str | None]:
    fastmcp_context = context.fastmcp_context
    if fastmcp_context is None:
        return None, None, None
    request_context = fastmcp_context.request_context
    meta = request_context.meta if request_context is not None else None
    extras = meta if isinstance(meta, dict) else {}
    request_id = fastmcp_context.origin_request_id
    return (
        str(request_id) if request_id is not None else None,
        extras.get("kis_activation_id"),
        extras.get("kis_project_id"),
    )


def _result_bytes(result: ResourceResult) -> bytes | None:
    if len(result.contents) != 1:
        return None
    content = result.contents[0].content
    return content.encode("utf-8") if isinstance(content, str) else bytes(content)


class SkillDeliveryTelemetryMiddleware(Middleware):
    def __init__(
        self,
        catalogue: SkillCatalogue,
        telemetry: SkillTelemetryStore,
        *,
        server_origin: str,
    ) -> None:
        self.catalogue = catalogue
        self.telemetry = telemetry
        self.server_origin = server_origin

    def _record(
        self,
        *,
        identity: _SkillResourceIdentity,
        uri: str,
        request_id: str | None,
        activation_id: str | None,
        project_id: str | None,
        started_ns: int,
        outcome: str,
        error_class: str | None = None,
        digest_verified: bool | None = None,
    ) -> None:
        snapshot_id = None
        content_sha256 = None
        if identity.skill_id is not None:
            try:
                version = self.catalogue.load_skill(identity.skill_id)
                snapshot_id = version.snapshot_id
                content_sha256 = version.sha256
            except SkillsError:
                pass
        self.telemetry.record(
            SkillTelemetryEvent(
                event_name=identity.event_name,
                source="observed",
                skill_id=identity.skill_id,
                snapshot_id=snapshot_id,
                content_sha256=content_sha256,
                project_id=project_id,
                activation_id=activation_id,
                request_id=request_id,
                outcome=outcome,
                duration_ms=_duration_ms(started_ns),
                error_class=error_class,
                delivery_path="mcp_resource",
                resource_uri=uri,
                resource_class=identity.resource_class,
                server_origin=self.server_origin,
                digest_verified=digest_verified,
            )
        )

    def _record_safely(self, **kwargs) -> None:
        try:
            self._record(**kwargs)
        except Exception:
            LOGGER.warning("Skills delivery telemetry persistence failed", exc_info=True)

    async def on_read_resource(self, context, call_next):
        uri = str(context.message.uri)
        identity = _identity(uri)
        if identity is None:
            return await call_next(context)
        started = perf_counter_ns()
        request_id, activation_id, project_id = _request_correlation(context)
        try:
            result = await call_next(context)
        except Exception as exc:
            error_class = exc.code if isinstance(exc, SkillsError) else type(exc).__name__
            self._record_safely(
                identity=identity,
                uri=uri,
                request_id=request_id,
                activation_id=activation_id,
                project_id=project_id,
                started_ns=started,
                outcome="error",
                error_class=error_class,
                digest_verified=False if identity.skill_id is not None else None,
            )
            raise

        verified: bool | None = None
        if identity.skill_id is not None and identity.relative_path is not None:
            try:
                evidence = self.catalogue.read_skill_file(
                    identity.skill_id, identity.relative_path
                )
                actual = _result_bytes(result)
                verified = (
                    actual is not None
                    and len(actual) == evidence.size
                    and hashlib.sha256(actual).hexdigest() == evidence.sha256
                )
            except SkillsError:
                verified = False
        self._record_safely(
            identity=identity,
            uri=uri,
            request_id=request_id,
            activation_id=activation_id,
            project_id=project_id,
            started_ns=started,
            outcome="success",
            digest_verified=verified,
        )
        return result


def register_skill_delivery_telemetry(
    server: FastMCP,
    catalogue: SkillCatalogue,
    telemetry: SkillTelemetryStore,
) -> SkillDeliveryTelemetryMiddleware:
    middleware = SkillDeliveryTelemetryMiddleware(
        catalogue,
        telemetry,
        server_origin=str(server.name),
    )
    server.add_middleware(middleware)
    return middleware


__all__ = ["SkillDeliveryTelemetryMiddleware", "register_skill_delivery_telemetry"]
