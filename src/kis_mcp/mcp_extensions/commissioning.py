from __future__ import annotations

import hashlib
import json
import logging
import os
import subprocess
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

from fastmcp import Client, FastMCP
from fastmcp.server.extensions import read_client_extension_settings
from mcp import types as mcp_types
from mcp.client.extension import ClientExtension
from pydantic import BaseModel, Field

LOGGER = logging.getLogger(__name__)

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_PROCESS_INSTANCE_ID = uuid4().hex


def _git_revision() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"],
            cwd=_REPOSITORY_ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    revision = result.stdout.strip().lower()
    if result.returncode != 0 or len(revision) != 40:
        return "unknown"
    return revision if all(char in "0123456789abcdef" for char in revision) else "unknown"


_PROCESS_SOURCE_REVISION = _git_revision()


def _digest(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def negotiated_extension_settings(request_context: object, identifier: str) -> dict[str, Any] | None:
    """Read per-request extension negotiation behind the FastMCP integration boundary."""
    sdk_context = getattr(request_context, "_srctx", None)
    if sdk_context is None:
        return None
    settings = read_client_extension_settings(sdk_context, identifier)
    return dict(settings) if settings is not None else None


class CommissioningStep(BaseModel):
    step: str
    outcome: str
    detail_code: str


class CommissioningProfileError(ValueError):
    def __init__(self, detail_code: str) -> None:
        if not detail_code or not detail_code.replace("_", "").isalnum():
            raise ValueError("commissioning detail_code must be a stable identifier")
        self.detail_code = detail_code
        super().__init__(detail_code)


class McpExtensionReceipt(BaseModel):
    receipt_id: str
    profile_id: str
    extension_id: str
    runtime_instance_id: str
    server_instance_id: str
    server_identity_fingerprint: str
    source_revision: str
    protocol_version: str
    extension_settings: dict[str, Any]
    extension_settings_fingerprint: str
    observed_at: str
    overall: str
    steps: tuple[CommissioningStep, ...]
    evidence: dict[str, Any] = Field(default_factory=dict)
    schema_version: int = 1
class McpExtensionReadiness(BaseModel):
    profile_id: str
    extension_id: str
    registered: bool
    runtime_instance_id: str
    server_instance_id: str
    server_identity_fingerprint: str
    source_revision: str
    last_receipt_id: str | None = None
    last_result: str | None = None
    last_matching: bool = False
    schema_version: int = 1


class CommissioningProfile(Protocol):
    profile_id: str
    extension_id: str

    def client_settings(self) -> Mapping[str, Any]: ...

    async def run(
        self,
        client: Client,
        discover: mcp_types.DiscoverResult,
        *,
        receipt_id: str,
        server_identity_fingerprint: str,
        server: FastMCP,
    ) -> tuple[tuple[CommissioningStep, ...], dict[str, Any]]: ...


class _NegotiatedExtension(ClientExtension):
    def __init__(self, identifier: str, settings: Mapping[str, Any]) -> None:
        self.identifier = identifier
        self._settings = dict(settings)

    def settings(self) -> dict[str, Any]:
        return dict(self._settings)
class McpExtensionCommissioningService:
    def __init__(self, server: FastMCP) -> None:
        self.server = server
        self.runtime_instance_id = _PROCESS_INSTANCE_ID
        self.server_instance_id = uuid4().hex
        self.source_revision = _PROCESS_SOURCE_REVISION
        self.server_identity_fingerprint = _digest(
            {
                "runtime_instance_id": self.runtime_instance_id,
                "server_instance_id": self.server_instance_id,
                "source_revision": self.source_revision,
                "pid": os.getpid(),
                "server_name": str(server.name),
            }
        )
        self._profiles: dict[str, CommissioningProfile] = {}
        self._last: dict[str, McpExtensionReceipt] = {}
        self._active_receipts: dict[str, str] = {}

    def register_profile(self, profile: CommissioningProfile) -> None:
        if not profile.profile_id or profile.profile_id in self._profiles:
            raise ValueError("commissioning profile_id must be unique")
        self._profiles[profile.profile_id] = profile

    def _matches_current(self, receipt: McpExtensionReceipt) -> bool:
        profile = self._profiles.get(receipt.profile_id)
        if profile is None:
            return False
        profile_matcher = getattr(profile, "receipt_matches_current", None)
        profile_matches = (
            bool(profile_matcher(receipt)) if callable(profile_matcher) else True
        )
        return bool(
            receipt.extension_id == profile.extension_id
            and receipt.runtime_instance_id == self.runtime_instance_id
            and receipt.server_instance_id == self.server_instance_id
            and receipt.server_identity_fingerprint == self.server_identity_fingerprint
            and receipt.source_revision == self.source_revision
            and receipt.protocol_version == mcp_types.LATEST_PROTOCOL_VERSION
            and receipt.extension_settings_fingerprint
            == _digest(dict(profile.client_settings()))
            and profile_matches
        )

    def receipt_matches_current(self, receipt: McpExtensionReceipt) -> bool:
        return self._matches_current(receipt)

    def is_active_receipt(self, receipt_id: str, profile_id: str | None = None) -> bool:
        active_profile = self._active_receipts.get(receipt_id)
        return active_profile is not None and (profile_id is None or active_profile == profile_id)

    async def commission(self, profile_id: str) -> McpExtensionReceipt:
        profile = self._profiles.get(profile_id)
        if profile is None:
            raise ValueError(f"unknown MCP extension commissioning profile: {profile_id}")
        observed_at = datetime.now(UTC).isoformat()
        receipt_id = _digest(
            {
                "profile_id": profile.profile_id,
                "extension_id": profile.extension_id,
                "runtime_instance_id": self.runtime_instance_id,
                "server_instance_id": self.server_instance_id,
                "server_identity_fingerprint": self.server_identity_fingerprint,
                "source_revision": self.source_revision,
                "observed_at": observed_at,
            }
        )
        client_extension = _NegotiatedExtension(
            profile.extension_id, profile.client_settings()
        )
        self._active_receipts[receipt_id] = profile.profile_id
        try:
            try:
                async with Client(
                    self.server,
                    extensions=[client_extension],
                    mode=mcp_types.LATEST_PROTOCOL_VERSION,
                ) as client:
                    discover = await client.session.send_request(
                        mcp_types.DiscoverRequest(), mcp_types.DiscoverResult
                    )
                    steps, evidence = await profile.run(
                        client,
                        discover,
                        receipt_id=receipt_id,
                        server_identity_fingerprint=self.server_identity_fingerprint,
                        server=self.server,
                    )
                    protocol_version = str(client.protocol_version)
            except Exception as exc:
                LOGGER.exception("MCP extension commissioning failed for %s", profile_id)
                detail_code = (
                    exc.detail_code
                    if isinstance(exc, CommissioningProfileError)
                    else "COMMISSIONING_INTERNAL_ERROR"
                )
                steps = (
                    CommissioningStep(
                        step="commissioning",
                        outcome="fail",
                        detail_code=detail_code,
                    ),
                )
                evidence = {}
                protocol_version = mcp_types.LATEST_PROTOCOL_VERSION
            settings = dict(profile.client_settings())
            receipt = McpExtensionReceipt(
                receipt_id=receipt_id,
                profile_id=profile.profile_id,
                extension_id=profile.extension_id,
                runtime_instance_id=self.runtime_instance_id,
                server_instance_id=self.server_instance_id,
                server_identity_fingerprint=self.server_identity_fingerprint,
                source_revision=self.source_revision,
                protocol_version=protocol_version,
                extension_settings=settings,
                extension_settings_fingerprint=_digest(settings),
                observed_at=observed_at,
                overall=(
                    "PASS"
                    if steps and all(item.outcome == "pass" for item in steps)
                    else "FAIL"
                ),
                steps=steps,
                evidence=evidence,
            )
            self._last[profile_id] = receipt
            return receipt
        finally:
            self._active_receipts.pop(receipt_id, None)

    def readiness(self, profile_id: str) -> McpExtensionReadiness:
        profile = self._profiles.get(profile_id)
        if profile is None:
            raise ValueError(f"unknown MCP extension commissioning profile: {profile_id}")
        last = self._last.get(profile_id)
        return McpExtensionReadiness(
            profile_id=profile.profile_id,
            extension_id=profile.extension_id,
            registered=True,
            runtime_instance_id=self.runtime_instance_id,
            server_instance_id=self.server_instance_id,
            server_identity_fingerprint=self.server_identity_fingerprint,
            source_revision=self.source_revision,
            last_receipt_id=last.receipt_id if last else None,
            last_result=last.overall if last else None,
            last_matching=self._matches_current(last) if last else False,
        )
def register_mcp_extension_commissioning(
    server: FastMCP,
) -> McpExtensionCommissioningService:
    service = McpExtensionCommissioningService(server)

    @server.tool
    async def commission_mcp_extension(profile_id: str) -> McpExtensionReceipt:
        """Run one registered MCP-extension profile through an in-process MCP client."""
        return await service.commission(profile_id)

    @server.tool
    def mcp_extension_commissioning_status(profile_id: str) -> McpExtensionReadiness:
        """Return bounded registration and current-runtime commissioning readiness."""
        return service.readiness(profile_id)

    return service


__all__ = [
    "CommissioningProfile",
    "CommissioningProfileError",
    "CommissioningStep",
    "McpExtensionCommissioningService",
    "McpExtensionReadiness",
    "McpExtensionReceipt",
    "negotiated_extension_settings",
    "register_mcp_extension_commissioning",
]
