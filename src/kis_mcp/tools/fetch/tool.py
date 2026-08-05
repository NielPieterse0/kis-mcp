from __future__ import annotations

import shutil
from collections.abc import Callable

from ..contracts import (
    ToolBoundary,
    ToolCapability,
    ToolDescriptor,
    ToolKind,
    ToolReadiness,
    ToolState,
)
from ..mcp_stdio import StdioMcpCommand
from .settings import FetchToolSettings

Which = Callable[[str], str | None]


def fetch_tool_descriptor(
    settings: FetchToolSettings,
    *,
    which: Which = shutil.which,
) -> ToolDescriptor:
    def build() -> StdioMcpCommand:
        return StdioMcpCommand(
            executable=settings.executable,
            arguments=settings.arguments,
            environment_names=settings.environment_names,
        )

    def readiness() -> ToolReadiness:
        details = {
            "package_name": settings.package_name,
            "package_version": settings.package_version,
            "external_network_required": True,
            "work_exposure_approved": False,
        }
        if not settings.enabled:
            return ToolReadiness(
                tool_id="mcp-fetch",
                state=ToolState.DISABLED,
                summary="Fetch MCP server is disabled because it requires external network access.",
                details=details,
            )
        if which(settings.executable) is None:
            return ToolReadiness(
                tool_id="mcp-fetch",
                state=ToolState.UNAVAILABLE,
                summary="Configured Fetch MCP executable is unavailable.",
                details=details,
            )
        return ToolReadiness(
            tool_id="mcp-fetch",
            state=ToolState.DEGRADED,
            summary="Fetch MCP server is installed but external network use is not approved for Work.",
            details=details,
        )

    return ToolDescriptor(
        tool_id="mcp-fetch",
        display_name="MCP Fetch Server",
        tool_kind=ToolKind.MCP_ADAPTER,
        boundary=ToolBoundary.APPROVED_EXTERNAL_SERVICE,
        authoritative_source=(
            f"{settings.source_repository}/tree/{settings.source_revision}/src/fetch"
        ),
        source_revision=settings.source_revision,
        capabilities=(
            ToolCapability(
                capability_id="web.fetch",
                description="Fetch and convert remote web content through the pinned MCP server.",
                effects=("external_network",),
                operation_names=("fetch",),
            ),
        ),
        builder=build,
        readiness_probe=readiness,
        enabled=settings.enabled,
    )


__all__ = ["fetch_tool_descriptor"]
