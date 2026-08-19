from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from kis_mcp.config import RuntimeConfig
from kis_mcp.housekeeping.operations import FastMCPInvoker

from .provider import HousekeepingLifecycleProvider, normalized_runtime_instance
from .service import HousekeepingApplyError, HousekeepingRuntimeService
from .settings import HousekeepingRuntimeSettings, load_housekeeping_runtime_settings
from .state import HousekeepingStateStore


def register_housekeeping_tools(
    server: FastMCP,
    service: HousekeepingRuntimeService,
) -> None:
    @server.tool
    def kis_housekeeping_status() -> dict:
        """Report unattended housekeeping host, cadence, receipts, and freshness."""
        return service.status()

    @server.tool
    def kis_housekeeping_receipt(receipt_id: str) -> dict:
        """Read one persisted housekeeping success or failure receipt by ID."""
        try:
            return service.receipt(receipt_id)
        except (KeyError, ValueError) as exc:
            raise ToolError(f"HOUSEKEEPING_RECEIPT_NOT_FOUND: {receipt_id}") from exc

    @server.tool
    async def kis_housekeeping_apply_receipt(receipt_id: str) -> dict:
        """Apply one fresh unchanged housekeeping preview with stable idempotency."""
        try:
            return await service.apply_receipt(receipt_id)
        except (HousekeepingApplyError, KeyError, ValueError) as exc:
            raise ToolError(f"HOUSEKEEPING_APPLY_REJECTED: {exc}") from exc


def compose_housekeeping_runtime(
    server: FastMCP,
    runtime: RuntimeConfig,
    *,
    environment: Mapping[str, str] | None = None,
    settings: HousekeepingRuntimeSettings | None = None,
) -> HousekeepingRuntimeService:
    selected = settings or load_housekeeping_runtime_settings()
    state_root = Path(runtime.state_root) / selected.state_namespace
    store = HousekeepingStateStore(state_root, retention=selected.receipt_retention)
    service = HousekeepingRuntimeService(
        selected,
        store,
        invoker=FastMCPInvoker(server),
        current_instance=normalized_runtime_instance(environment),
    )
    server.add_provider(HousekeepingLifecycleProvider(service))
    register_housekeeping_tools(server, service)
    return service


__all__ = [
    "compose_housekeeping_runtime",
    "register_housekeeping_tools",
]
