from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

from fastmcp import Client, FastMCP
from mcp import types as mcp_types
from mcp.shared.exceptions import MCPError
from mcp_types import METHOD_NOT_FOUND

from ..mcp_extensions import CommissioningProfileError, CommissioningStep, McpExtensionReceipt
from .catalogue import SkillCatalogue
from .sep2640 import (
    SEP2640_BASELINE,
    SEP2640_EXTENSION_ID,
    ResourcesDirectoryReadParams,
    ResourcesDirectoryReadResult,
    SkillsGetParams,
    SkillsGetResult,
    SkillsListParams,
    SkillsListResult,
    _skill_entry,
    skill_resource_set_fingerprint,
    verify_advertised_skill_resource,
)
from .telemetry import SkillTelemetryEvent, SkillTelemetryStore

SEP2640_COMMISSIONING_PROFILE = "sep2640-skills"


def _settings_fingerprint(settings: dict[str, Any]) -> str:
    encoded = json.dumps(settings, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _content_bytes(contents) -> bytes:
    if len(contents) != 1:
        raise ValueError("commissioning resource read must return exactly one content item")
    item = contents[0]
    if isinstance(item, mcp_types.TextResourceContents):
        return item.text.encode("utf-8")
    if isinstance(item, mcp_types.BlobResourceContents):
        return base64.b64decode(item.blob, validate=True)
    raise TypeError("commissioning resource content type is unsupported")
class Sep2640SkillsCommissioningProfile:
    profile_id = SEP2640_COMMISSIONING_PROFILE
    extension_id = SEP2640_EXTENSION_ID

    def __init__(
        self,
        catalogue: SkillCatalogue,
        telemetry: SkillTelemetryStore | None = None,
    ) -> None:
        self.catalogue = catalogue
        self.telemetry = telemetry

    def client_settings(self) -> dict[str, Any]:
        return {"directoryRead": True, "baseline": SEP2640_BASELINE}

    def _current_canonical_skill_id(self) -> str | None:
        cursor: str | None = None
        selected: str | None = None
        while True:
            page = self.catalogue.list_skills(
                limit=self.catalogue.config.limits.list_max_limit,
                cursor=cursor,
            )
            for card in page.skills:
                candidate = str(card.id)
                if selected is None or candidate < selected:
                    selected = candidate
            if page.next_cursor is None:
                return selected
            cursor = page.next_cursor

    def receipt_matches_current(self, receipt: McpExtensionReceipt) -> bool:
        if receipt.overall != "PASS":
            return False
        skill_id = receipt.evidence.get("skill_id")
        canonical_uri = receipt.evidence.get("canonical_skill_uri")
        resource_set_fingerprint = receipt.evidence.get("resource_set_fingerprint")
        if not all(isinstance(value, str) and value for value in (skill_id, canonical_uri, resource_set_fingerprint)):
            return False
        if self._current_canonical_skill_id() != skill_id:
            return False
        try:
            current = _skill_entry(self.catalogue, skill_id)
        except Exception:
            return False
        return bool(
            str(current.uri) == canonical_uri
            and skill_resource_set_fingerprint(receipt.server_identity_fingerprint, current)
            == resource_set_fingerprint
        )

    def _record_commissioned(
        self,
        *,
        skill_id: str,
        receipt_id: str,
        protocol_version: str,
        server_identity_fingerprint: str,
        canonical_uri: str,
        resource_set_fingerprint: str,
    ) -> None:
        if self.telemetry is None:
            return
        version = self.catalogue.load_skill(skill_id)
        self.telemetry.record(
            SkillTelemetryEvent(
                event_name="skill_commissioned",
                source="observed",
                skill_id=skill_id,
                snapshot_id=version.snapshot_id,
                content_sha256=version.sha256,
                delivery_path="mcp_resource",
                server_identity_fingerprint=server_identity_fingerprint,
                protocol_version=protocol_version,
                extension_id=SEP2640_EXTENSION_ID,
                extension_settings_fingerprint=_settings_fingerprint(self.client_settings()),
                commissioning_receipt_id=receipt_id,
                canonical_skill_uri=canonical_uri,
                resource_set_fingerprint=resource_set_fingerprint,
                integrity_proof="live_commissioning",
            )
        )

    def _record_negative_negotiation(
        self,
        *,
        skill_id: str,
        receipt_id: str,
        protocol_version: str,
        server_identity_fingerprint: str,
        canonical_uri: str,
        resource_set_fingerprint: str,
    ) -> None:
        if self.telemetry is None:
            return
        version = self.catalogue.load_skill(skill_id)
        self.telemetry.record(
            SkillTelemetryEvent(
                event_name="skills_negative_negotiation_observed",
                source="observed",
                skill_id=skill_id,
                snapshot_id=version.snapshot_id,
                content_sha256=version.sha256,
                delivery_path="mcp_resource",
                server_identity_fingerprint=server_identity_fingerprint,
                protocol_version=protocol_version,
                extension_id=SEP2640_EXTENSION_ID,
                extension_settings_fingerprint=_settings_fingerprint(self.client_settings()),
                commissioning_receipt_id=receipt_id,
                canonical_skill_uri=canonical_uri,
                resource_set_fingerprint=resource_set_fingerprint,
                integrity_proof="negative_negotiation",
            )
        )

    async def run(
        self,
        client: Client,
        discover: mcp_types.DiscoverResult,
        *,
        receipt_id: str,
        server_identity_fingerprint: str,
        server: FastMCP,
    ) -> tuple[tuple[CommissioningStep, ...], dict[str, Any]]:
        meta = {"kis_commissioning_receipt_id": receipt_id}
        extensions = discover.capabilities.extensions or {}
        advertised = extensions.get(SEP2640_EXTENSION_ID)
        expected = {"directoryRead": True, "baseline": SEP2640_BASELINE}
        if advertised != expected:
            raise CommissioningProfileError("SEP2640_ADVERTISEMENT_MISMATCH")
        steps: list[CommissioningStep] = [
            CommissioningStep(
                step="server/discover",
                outcome="pass",
                detail_code="SEP2640_ADVERTISED",
            )
        ]
        listed = await client.session.send_request(
            mcp_types.Request(
                method="skills/list", params=SkillsListParams(meta=meta)
            ),
            SkillsListResult,
        )
        if not listed.skills:
            raise CommissioningProfileError("SEP2640_NO_CANONICAL_SKILL")
        selected = sorted(listed.skills, key=lambda item: str(item.uri))[0]
        skill_id = str(selected.uri).split("/")[-2]
        steps.append(
            CommissioningStep(step="skills/list", outcome="pass", detail_code="SKILL_SELECTED")
        )
        got = await client.session.send_request(
            mcp_types.Request(
                method="skills/get",
                params=SkillsGetParams(uri=selected.uri, meta=meta),
            ),
            SkillsGetResult,
        )
        if str(got.skill.uri) != str(selected.uri):
            raise CommissioningProfileError("SEP2640_GET_IDENTITY_MISMATCH")
        steps.append(
            CommissioningStep(step="skills/get", outcome="pass", detail_code="SKILL_IDENTITY_OK")
        )

        resource_contents = await client.read_resource(str(got.skill.uri), meta=meta)
        resource_bytes = _content_bytes(resource_contents)
        verify_advertised_skill_resource(got.skill, str(got.skill.uri), resource_bytes)
        steps.append(
            CommissioningStep(
                step="resources/read",
                outcome="pass",
                detail_code="ENTRYPOINT_INTEGRITY_OK",
            )
        )

        if advertised.get("directoryRead") is True:
            directory_uri = f"skill:///{skill_id}/"
            directory = await client.session.send_request(
                mcp_types.Request(
                    method="resources/directory/read",
                    params=ResourcesDirectoryReadParams(uri=directory_uri, meta=meta),
                ),
                ResourcesDirectoryReadResult,
            )
            if not any(str(item.uri) == str(got.skill.uri) for item in directory.resources):
                raise CommissioningProfileError("SEP2640_DIRECTORY_ENTRYPOINT_MISSING")
            steps.append(
                CommissioningStep(
                    step="resources/directory/read",
                    outcome="pass",
                    detail_code="DIRECTORY_READ_OK",
                )
            )
        resource_set = skill_resource_set_fingerprint(
            server_identity_fingerprint, got.skill
        )
        async with Client(server, mode=mcp_types.LATEST_PROTOCOL_VERSION) as unnegotiated:
            negative_controls = (
                (
                    "skills/list",
                    SkillsListParams(),
                    SkillsListResult,
                ),
                (
                    "skills/get",
                    SkillsGetParams(uri=got.skill.uri),
                    SkillsGetResult,
                ),
                (
                    "resources/directory/read",
                    ResourcesDirectoryReadParams(uri=f"skill:///{skill_id}/"),
                    ResourcesDirectoryReadResult,
                ),
            )
            for method, params, result_type in negative_controls:
                try:
                    await unnegotiated.session.send_request(
                        mcp_types.Request(method=method, params=params),
                        result_type,
                    )
                except MCPError as exc:
                    if exc.code != METHOD_NOT_FOUND:
                        raise
                else:
                    raise CommissioningProfileError("SEP2640_NEGOTIATION_CONTROL_FAILED")
                steps.append(
                    CommissioningStep(
                        step=f"{method}:unnegotiated",
                        outcome="pass",
                        detail_code="METHOD_NOT_FOUND_CONFIRMED",
                    )
                )
        self._record_negative_negotiation(
            skill_id=skill_id,
            receipt_id=receipt_id,
            protocol_version=str(client.protocol_version),
            server_identity_fingerprint=server_identity_fingerprint,
            canonical_uri=str(got.skill.uri),
            resource_set_fingerprint=resource_set,
        )
        self._record_commissioned(
            skill_id=skill_id,
            receipt_id=receipt_id,
            protocol_version=str(client.protocol_version),
            server_identity_fingerprint=server_identity_fingerprint,
            canonical_uri=str(got.skill.uri),
            resource_set_fingerprint=resource_set,
        )
        evidence = {
            "skill_id": skill_id,
            "canonical_skill_uri": str(got.skill.uri),
            "resource_count": len(got.skill.resources),
            "resource_set_fingerprint": resource_set,
            "advertised_settings": advertised,
            "negative_negotiation": "METHOD_NOT_FOUND",
        }
        return tuple(steps), evidence


__all__ = ["SEP2640_COMMISSIONING_PROFILE", "Sep2640SkillsCommissioningProfile"]
