from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Callable
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
    if len(parts) == 2 and parts[1] == "resource":
        values = parse_qs(parsed.query, keep_blank_values=True).get("path", [])
        if len(values) == 1 and values[0]:
            relative_path = values[0]
            return _SkillResourceIdentity(
                parts[0], relative_path, _classify(relative_path), "skill_resource_read"
            )
    if len(parts) >= 2:
        relative_path = "/".join(parts[1:])
        return _SkillResourceIdentity(
            parts[0],
            relative_path,
            _classify(relative_path),
            "skill_loaded" if relative_path == "SKILL.md" else "skill_resource_read",
        )
    return None


def _request_correlation(
    context: MiddlewareContext,
) -> tuple[str | None, str | None, str | None, str | None, str | None]:
    fastmcp_context = context.fastmcp_context
    if fastmcp_context is None:
        return None, None, None, None, None
    request_context = fastmcp_context.request_context
    meta = request_context.meta if request_context is not None else None
    extras = meta if isinstance(meta, dict) else {}
    request_id = fastmcp_context.origin_request_id
    protocol_version = getattr(request_context, "protocol_version", None)
    return (
        str(request_id) if request_id is not None else None,
        extras.get("kis_activation_id"),
        extras.get("kis_project_id"),
        extras.get("kis_commissioning_receipt_id"),
        str(protocol_version) if protocol_version is not None else None,
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
        server_identity_fingerprint: str | None = None,
        extension_id: str | None = None,
        resource_set_fingerprint_resolver: Callable[[str], str] | None = None,
        negotiated_settings_resolver: Callable[[object, str], dict[str, object] | None] | None = None,
        commissioning_receipt_validator: Callable[[str], bool] | None = None,
    ) -> None:
        self.catalogue = catalogue
        self.telemetry = telemetry
        self.server_origin = server_origin
        self.server_identity_fingerprint = server_identity_fingerprint
        self.extension_id = extension_id
        self.resource_set_fingerprint_resolver = resource_set_fingerprint_resolver
        self.negotiated_settings_resolver = negotiated_settings_resolver
        self.commissioning_receipt_validator = commissioning_receipt_validator

    def _record(
        self,
        *,
        identity: _SkillResourceIdentity,
        uri: str,
        request_id: str | None,
        activation_id: str | None,
        project_id: str | None,
        commissioning_receipt_id: str | None,
        protocol_version: str | None,
        negotiated_extension_id: str | None,
        negotiated_extension_settings_fingerprint: str | None,
        started_ns: int,
        outcome: str,
        error_class: str | None = None,
        digest_verified: bool | None = None,
    ) -> None:
        snapshot_id = None
        content_sha256 = None
        resource_set_fingerprint = None
        if identity.skill_id is not None:
            try:
                version = self.catalogue.load_skill(identity.skill_id)
                snapshot_id = version.snapshot_id
                content_sha256 = version.sha256
                if self.resource_set_fingerprint_resolver is not None:
                    resource_set_fingerprint = self.resource_set_fingerprint_resolver(
                        identity.skill_id
                    )
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
                server_identity_fingerprint=self.server_identity_fingerprint,
                protocol_version=protocol_version,
                extension_id=negotiated_extension_id,
                extension_settings_fingerprint=negotiated_extension_settings_fingerprint,
                commissioning_receipt_id=commissioning_receipt_id,
                canonical_skill_uri=(
                    f"skill:///{identity.skill_id}/SKILL.md"
                    if identity.skill_id is not None
                    else None
                ),
                resource_set_fingerprint=resource_set_fingerprint,
                integrity_proof=(
                    "ordinary_digest" if digest_verified is not None else None
                ),
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
        (
            request_id,
            activation_id,
            project_id,
            commissioning_receipt_id,
            protocol_version,
        ) = _request_correlation(context)
        if (
            commissioning_receipt_id is not None
            and self.commissioning_receipt_validator is not None
            and not self.commissioning_receipt_validator(commissioning_receipt_id)
        ):
            commissioning_receipt_id = None
        request_context = (
            context.fastmcp_context.request_context
            if context.fastmcp_context is not None
            else None
        )
        negotiated_settings = (
            self.negotiated_settings_resolver(request_context, self.extension_id)
            if request_context is not None
            and self.extension_id is not None
            and self.negotiated_settings_resolver is not None
            else None
        )
        negotiated_extension_id = self.extension_id if negotiated_settings is not None else None
        negotiated_extension_settings_fingerprint = (
            hashlib.sha256(
                json.dumps(
                    negotiated_settings, sort_keys=True, separators=(",", ":")
                ).encode("utf-8")
            ).hexdigest()
            if negotiated_settings is not None
            else None
        )
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
                commissioning_receipt_id=commissioning_receipt_id,
                protocol_version=protocol_version,
                negotiated_extension_id=negotiated_extension_id,
                negotiated_extension_settings_fingerprint=negotiated_extension_settings_fingerprint,
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
            commissioning_receipt_id=commissioning_receipt_id,
            protocol_version=protocol_version,
            negotiated_extension_id=negotiated_extension_id,
            negotiated_extension_settings_fingerprint=negotiated_extension_settings_fingerprint,
            started_ns=started,
            outcome="success",
            digest_verified=verified,
        )
        return result


def register_skill_delivery_telemetry(
    server: FastMCP,
    catalogue: SkillCatalogue,
    telemetry: SkillTelemetryStore,
    *,
    server_identity_fingerprint: str | None = None,
    extension_id: str | None = None,
    resource_set_fingerprint_resolver: Callable[[str], str] | None = None,
    negotiated_settings_resolver: Callable[[object, str], dict[str, object] | None] | None = None,
    commissioning_receipt_validator: Callable[[str], bool] | None = None,
) -> SkillDeliveryTelemetryMiddleware:
    middleware = SkillDeliveryTelemetryMiddleware(
        catalogue,
        telemetry,
        server_origin=str(server.name),
        server_identity_fingerprint=server_identity_fingerprint,
        extension_id=extension_id,
        resource_set_fingerprint_resolver=resource_set_fingerprint_resolver,
        negotiated_settings_resolver=negotiated_settings_resolver,
        commissioning_receipt_validator=commissioning_receipt_validator,
    )
    server.add_middleware(middleware)
    return middleware


__all__ = ["SkillDeliveryTelemetryMiddleware", "register_skill_delivery_telemetry"]
