from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Sequence
from typing import Any, Literal
from urllib.parse import unquote, urlparse

import mcp.types as mcp_types
from fastmcp import FastMCP
from fastmcp.resources import Resource
from fastmcp.server.extensions import MethodBinding, ServerExtension
from fastmcp.server.providers import Provider
from mcp.server.context import ServerRequestContext
from mcp.shared.exceptions import MCPError
from mcp_types import METHOD_NOT_FOUND
from pydantic import AnyUrl, BaseModel

from .catalogue import SkillCatalogue
from .errors import SkillsError
from .frontmatter import parse_skill_frontmatter
from .telemetry import SkillTelemetryEvent, SkillTelemetryStore

LOGGER = logging.getLogger(__name__)

SEP2640_EXTENSION_ID = "io.modelcontextprotocol/skills"
SEP2640_BASELINE = "draft-v1-2026-08-25"
SEP2640_MAX_RESOURCES = 512
SEP2640_MAX_SKILL_BYTES = 16_777_216


class SkillResourceDigest(BaseModel):
    uri: AnyUrl
    digest: str
    size: int


class SkillEntry(BaseModel):
    uri: AnyUrl
    frontmatter: dict[str, Any]
    resources: list[SkillResourceDigest]


class SkillsListParams(mcp_types.PaginatedRequestParams):
    pass


class SkillsListResult(mcp_types.PaginatedResult):
    result_type: Literal["complete"] = "complete"
    ttl_ms: int = 0
    cache_scope: Literal["private"] = "private"
    skills: list[SkillEntry]


class SkillsGetParams(mcp_types.RequestParams):
    uri: AnyUrl


class SkillsGetResult(mcp_types.Result):
    result_type: Literal["complete"] = "complete"
    skill: SkillEntry


class ResourcesDirectoryReadParams(mcp_types.PaginatedRequestParams):
    uri: AnyUrl


class ResourcesDirectoryReadResult(mcp_types.PaginatedResult):
    result_type: Literal["complete"] = "complete"
    ttl_ms: int = 0
    cache_scope: Literal["private"] = "private"
    resources: list[mcp_types.Resource]


def _digest(value: str) -> str:
    return f"sha256:{value}"


def _file_uri(skill_id: str, relative_path: str) -> str:
    return f"skill:///{skill_id}/{relative_path}"


def _skill_entry(catalogue: SkillCatalogue, skill_id: str) -> SkillEntry:
    source = catalogue._entry(skill_id)
    if len(source.files) > SEP2640_MAX_RESOURCES:
        raise SkillsError(
            "SKILLS_SEP2640_RESOURCE_LIMIT_EXCEEDED",
            f"SEP-2640 skills may contain at most {SEP2640_MAX_RESOURCES} resources",
        )
    total_size = sum(item.size for item in source.files)
    if total_size > SEP2640_MAX_SKILL_BYTES:
        raise SkillsError(
            "SKILLS_SEP2640_SIZE_LIMIT_EXCEEDED",
            f"SEP-2640 skills may contain at most {SEP2640_MAX_SKILL_BYTES} bytes",
        )
    frontmatter = dict(parse_skill_frontmatter(source.content))
    resources = [
        SkillResourceDigest(
            uri=_file_uri(source.id, item.path),
            digest=_digest(item.sha256),
            size=item.size,
        )
        for item in source.files
    ]
    return SkillEntry(
        uri=_file_uri(source.id, "SKILL.md"),
        frontmatter=frontmatter,
        resources=resources,
    )


def _skill_id_from_entrypoint_uri(uri: str) -> str:
    parsed = urlparse(uri)
    if parsed.scheme != "skill" or parsed.netloc or parsed.query or parsed.fragment:
        raise SkillsError("SKILLS_RESOURCE_URI_INVALID", "Skill URI is not served by KIS")
    parts = [unquote(part) for part in parsed.path.split("/") if part]
    if len(parts) != 2 or parts[1] != "SKILL.md":
        raise SkillsError("SKILLS_RESOURCE_URI_INVALID", "Skill URI must identify SKILL.md")
    return parts[0]


def _resource_target(uri: str) -> tuple[str, str, bool]:
    parsed = urlparse(uri)
    if parsed.scheme != "skill" or parsed.netloc or parsed.query or parsed.fragment:
        raise SkillsError("SKILLS_RESOURCE_URI_INVALID", "Resource URI is not served by KIS")
    decoded = [unquote(part) for part in parsed.path.split("/") if part]
    if not decoded:
        raise SkillsError("SKILLS_RESOURCE_URI_INVALID", "Skill resource URI is incomplete")
    skill_id = decoded[0]
    relative = "/".join(decoded[1:])
    return skill_id, relative, parsed.path.endswith("/")


def _mime_type(relative_path: str) -> str:
    lowered = relative_path.casefold()
    if relative_path == "SKILL.md" or lowered.endswith(".md"):
        return "text/markdown"
    if lowered.endswith(".py"):
        return "text/x-python"
    if lowered.endswith(".json"):
        return "application/json"
    if lowered.endswith(".png"):
        return "image/png"
    return "application/octet-stream"


class SkillDirectResourceProvider(Provider):
    def __init__(self, catalogue: SkillCatalogue) -> None:
        super().__init__()
        self.catalogue = catalogue

    async def _get_resource(self, uri: str, version=None) -> Resource | None:
        try:
            skill_id, relative_path, is_directory = _resource_target(uri)
            if is_directory or not relative_path:
                return None
            self.catalogue._entry(skill_id)
            self.catalogue.read_skill_file(skill_id, relative_path)
        except SkillsError:
            return None

        def read() -> bytes:
            return self.catalogue.read_skill_resource_bytes(skill_id, relative_path)

        return Resource.from_function(
            read,
            uri=uri,
            name=relative_path.rsplit("/", 1)[-1],
            mime_type=_mime_type(relative_path),
        )


def _directory_children(catalogue: SkillCatalogue, uri: str) -> list[mcp_types.Resource]:
    skill_id, relative_path, is_directory = _resource_target(uri)
    if not is_directory:
        raise SkillsError("SKILLS_RESOURCE_URI_INVALID", "Directory URI must end with '/'")
    source = catalogue._entry(skill_id)
    prefix = f"{relative_path.rstrip('/')}/" if relative_path else ""
    children: dict[str, mcp_types.Resource] = {}
    for item in source.files:
        if not item.path.startswith(prefix):
            continue
        remainder = item.path[len(prefix) :]
        if not remainder:
            continue
        head, separator, _tail = remainder.partition("/")
        child_path = f"{prefix}{head}"
        if separator:
            child_uri = _file_uri(skill_id, child_path + "/")
            children.setdefault(
                child_uri,
                mcp_types.Resource(uri=child_uri, name=head, mimeType="inode/directory"),
            )
        else:
            child_uri = _file_uri(skill_id, child_path)
            children[child_uri] = mcp_types.Resource(
                uri=child_uri,
                name=head,
                mimeType=_mime_type(child_path),
                size=item.size,
            )
    return [children[key] for key in sorted(children)]


def _directory_cursor(catalogue: SkillCatalogue, uri: str, offset: int) -> str:
    binding = hashlib.sha256(uri.encode("utf-8")).hexdigest()[:16]
    return f"{catalogue.snapshot_id}:{binding}:{offset}"


def _directory_offset(catalogue: SkillCatalogue, uri: str, cursor: str | None) -> int:
    if cursor is None:
        return 0
    parts = cursor.split(":")
    binding = hashlib.sha256(uri.encode("utf-8")).hexdigest()[:16]
    if (
        len(parts) != 3
        or parts[0] != catalogue.snapshot_id
        or parts[1] != binding
        or not parts[2].isdecimal()
    ):
        raise SkillsError("SKILLS_CURSOR_INVALID", "Directory cursor is stale or invalid")
    return int(parts[2])


class Sep2640SkillsExtension(ServerExtension):
    identifier = SEP2640_EXTENSION_ID

    def __init__(
        self,
        catalogue: SkillCatalogue,
        telemetry: SkillTelemetryStore | None = None,
        *,
        server_identity_fingerprint: str | None = None,
    ) -> None:
        self.catalogue = catalogue
        self.telemetry = telemetry
        self.server_identity_fingerprint = server_identity_fingerprint

    def _record_protocol_event(
        self,
        event_name: str,
        ctx: ServerRequestContext,
        params: mcp_types.RequestParams,
        *,
        skill_id: str | None = None,
        canonical_skill_uri: str | None = None,
        resource_set_fingerprint: str | None = None,
    ) -> None:
        if self.telemetry is None:
            return
        try:
            version = self.catalogue.load_skill(skill_id) if skill_id else None
            meta = params.meta if isinstance(params.meta, dict) else {}
            settings = self.client_settings(ctx) or {}
            settings_hash = hashlib.sha256(
                json.dumps(settings, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            self.telemetry.record(
                SkillTelemetryEvent(
                    event_name=event_name,
                    source="observed",
                    skill_id=skill_id,
                    snapshot_id=version.snapshot_id if version else None,
                    content_sha256=version.sha256 if version else None,
                    project_id=meta.get("kis_project_id"),
                    activation_id=meta.get("kis_activation_id"),
                    delivery_path="mcp_resource",
                    server_identity_fingerprint=self.server_identity_fingerprint,
                    protocol_version=str(ctx.protocol_version),
                    extension_id=SEP2640_EXTENSION_ID,
                    extension_settings_fingerprint=settings_hash,
                    commissioning_receipt_id=meta.get("kis_commissioning_receipt_id"),
                    canonical_skill_uri=canonical_skill_uri,
                    resource_set_fingerprint=resource_set_fingerprint,
                )
            )
        except Exception:
            LOGGER.warning("SEP-2640 protocol telemetry persistence failed", exc_info=True)

    def settings(self) -> dict[str, Any]:
        return {"directoryRead": True, "baseline": SEP2640_BASELINE}

    def methods(self) -> Sequence[MethodBinding]:
        versions = frozenset({mcp_types.LATEST_PROTOCOL_VERSION})
        return (
            MethodBinding("skills/list", SkillsListParams, self._skills_list, versions),
            MethodBinding("skills/get", SkillsGetParams, self._skills_get, versions),
            MethodBinding(
                "resources/directory/read",
                ResourcesDirectoryReadParams,
                self._directory_read,
                versions,
            ),
        )

    def _require_negotiated(self, ctx: ServerRequestContext) -> None:
        if self.client_settings(ctx) is None:
            raise MCPError(
                code=METHOD_NOT_FOUND,
                message=f"Extension {self.identifier!r} was not negotiated for this request.",
            )

    async def _skills_list(
        self, ctx: ServerRequestContext, params: SkillsListParams
    ) -> SkillsListResult:
        self._require_negotiated(ctx)
        page = self.catalogue.list_skills(
            limit=self.catalogue.config.limits.list_max_limit,
            cursor=params.cursor,
        )
        entries: list[SkillEntry] = []
        for card in page.skills:
            try:
                entries.append(_skill_entry(self.catalogue, card.id))
            except SkillsError as exc:
                if exc.code not in {
                    "SKILLS_SEP2640_RESOURCE_LIMIT_EXCEEDED",
                    "SKILLS_SEP2640_SIZE_LIMIT_EXCEEDED",
                }:
                    raise
        self._record_protocol_event("skills_list_observed", ctx, params)
        return SkillsListResult(skills=entries, nextCursor=page.next_cursor)

    async def _skills_get(
        self, ctx: ServerRequestContext, params: SkillsGetParams
    ) -> SkillsGetResult:
        self._require_negotiated(ctx)
        skill_id = _skill_id_from_entrypoint_uri(str(params.uri))
        entry = _skill_entry(self.catalogue, skill_id)
        identity = (
            skill_resource_set_fingerprint(self.server_identity_fingerprint, entry)
            if self.server_identity_fingerprint
            else None
        )
        self._record_protocol_event(
            "skills_get_observed",
            ctx,
            params,
            skill_id=skill_id,
            canonical_skill_uri=str(entry.uri),
            resource_set_fingerprint=identity,
        )
        return SkillsGetResult(skill=entry)

    async def _directory_read(
        self, ctx: ServerRequestContext, params: ResourcesDirectoryReadParams
    ) -> ResourcesDirectoryReadResult:
        self._require_negotiated(ctx)
        uri = str(params.uri)
        children = _directory_children(self.catalogue, uri)
        offset = _directory_offset(self.catalogue, uri, params.cursor)
        if offset > len(children):
            raise SkillsError("SKILLS_CURSOR_INVALID", "Directory cursor is outside this listing")
        page_size = self.catalogue.config.limits.list_max_limit
        page = children[offset : offset + page_size]
        next_cursor = (
            _directory_cursor(self.catalogue, uri, offset + page_size)
            if offset + page_size < len(children)
            else None
        )
        skill_id, _relative_path, _is_directory = _resource_target(uri)
        self._record_protocol_event(
            "skill_directory_read",
            ctx,
            params,
            skill_id=skill_id,
            canonical_skill_uri=_file_uri(skill_id, "SKILL.md"),
        )
        return ResourcesDirectoryReadResult(resources=page, nextCursor=next_cursor)


def register_sep2640_extension(
    server: FastMCP,
    catalogue: SkillCatalogue,
    telemetry: SkillTelemetryStore | None = None,
    *,
    server_identity_fingerprint: str | None = None,
) -> None:
    """Register the draft SEP-2640 transport binding over the KIS catalogue."""
    server.add_provider(SkillDirectResourceProvider(catalogue))
    server.add_extension(
        Sep2640SkillsExtension(
            catalogue,
            telemetry,
            server_identity_fingerprint=server_identity_fingerprint,
        )
    )


__all__ = [
    "SEP2640_BASELINE",
    "SEP2640_EXTENSION_ID",
    "ResourcesDirectoryReadParams",
    "ResourcesDirectoryReadResult",
    "Sep2640SkillsExtension",
    "SkillEntry",
    "SkillResourceDigest",
    "SkillsGetParams",
    "SkillsGetResult",
    "SkillsListParams",
    "SkillsListResult",
    "catalogue_skill_resource_set_fingerprint",
    "register_sep2640_extension",
    "skill_requires_reapproval",
    "skill_resource_set_fingerprint",
    "verify_advertised_skill_resource",
]


def catalogue_skill_resource_set_fingerprint(
    catalogue: SkillCatalogue, skill_id: str, server_identity: str
) -> str:
    """Bind one canonical catalogue skill to server identity and its full resource set."""
    return skill_resource_set_fingerprint(server_identity, _skill_entry(catalogue, skill_id))


def skill_resource_set_fingerprint(server_identity: str, entry: SkillEntry) -> str:
    """Bind approval to server identity, skill URI, and the complete resource set."""
    if not isinstance(server_identity, str) or not server_identity.strip():
        raise ValueError("server_identity must be non-empty text")
    payload = {
        "server_identity": server_identity.strip(),
        "skill_uri": str(entry.uri),
        "resources": [
            {"uri": str(item.uri), "digest": item.digest, "size": item.size}
            for item in sorted(entry.resources, key=lambda item: str(item.uri))
        ],
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def skill_requires_reapproval(
    server_identity: str, entry: SkillEntry, approved_fingerprint: str
) -> bool:
    return skill_resource_set_fingerprint(server_identity, entry) != approved_fingerprint


def verify_advertised_skill_resource(entry: SkillEntry, uri: str, data: bytes) -> None:
    """Verify fetched bytes against the advertised manifest and frontmatter."""
    resource = next((item for item in entry.resources if str(item.uri) == uri), None)
    if resource is None:
        raise SkillsError(
            "SKILLS_EXTENSION_RESOURCE_UNLISTED",
            "Fetched resource is not in the advertised skill resource set",
        )
    if len(data) != resource.size or _digest(hashlib.sha256(data).hexdigest()) != resource.digest:
        raise SkillsError(
            "SKILLS_EXTENSION_DIGEST_MISMATCH",
            "Fetched resource does not match its advertised digest and size",
        )
    if uri == str(entry.uri):
        try:
            content = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SkillsError(
                "SKILLS_EXTENSION_FRONTMATTER_MISMATCH",
                "Fetched SKILL.md is not UTF-8 text",
            ) from exc
        if dict(parse_skill_frontmatter(content)) != entry.frontmatter:
            raise SkillsError(
                "SKILLS_EXTENSION_FRONTMATTER_MISMATCH",
                "Fetched SKILL.md frontmatter differs from the advertised entry",
            )
