from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from ..config import RuntimeConfig
from ..models import HealthResponse, QuarantineListResponse, QuarantineResponse
from ..providers.runtime import ProviderRuntimeComposition, provider_runtime_status
from ..providers.service import ProviderService
from ..quarantine import QuarantineError, QuarantineService
from ..workflows.verification.platform import register_platform_verification
from .foundation import health_response, quarantine_payload, quarantine_response


def register_gateway_operations(
    server: FastMCP,
    *,
    runtime: RuntimeConfig,
    launch: dict[str, Any],
    quarantine: QuarantineService,
    provider_service: ProviderService,
    provider_composition: ProviderRuntimeComposition,
) -> None:
    @server.tool
    def kis_health() -> HealthResponse:
        """Report local provider, policy, and generated-state readiness."""
        return health_response(runtime, launch)

    @server.tool
    def kis_quarantine_path(path: str) -> QuarantineResponse:
        """Move one path into recoverable local quarantine."""
        try:
            return quarantine_response(quarantine.quarantine(path))
        except QuarantineError as exc:
            raise ToolError(f"HR-003_QUARANTINE_FAILED: {exc}") from exc

    @server.tool
    def kis_list_quarantine(limit: int = 50) -> QuarantineListResponse:
        """List bounded recoverable quarantine records."""
        return QuarantineListResponse(
            records=tuple(quarantine_response(item) for item in quarantine.list_records(limit=limit))
        )

    @server.tool
    def kis_restore_quarantine(operation_id: str) -> QuarantineResponse:
        """Restore one quarantine record without overwriting its original path."""
        try:
            return quarantine_response(quarantine.restore(operation_id))
        except QuarantineError as exc:
            raise ToolError(f"HR-003_QUARANTINE_FAILED: {exc}") from exc

    register_platform_verification(server, runtime)

    status_server = FastMCP("kis-mcp-provider-status")

    @status_server.tool
    def kis_provider_status() -> dict[str, Any]:
        """Report provider readiness, mount state, and actionable connection steps."""
        return provider_runtime_status(provider_service, provider_composition)

    server.mount(status_server)


def quarantine_many_payloads(
    quarantine: QuarantineService,
    paths: Sequence[str],
) -> list[dict[str, Any]]:
    return [quarantine_payload(item) for item in quarantine.quarantine_many(paths)]


__all__ = ["quarantine_many_payloads", "register_gateway_operations"]
