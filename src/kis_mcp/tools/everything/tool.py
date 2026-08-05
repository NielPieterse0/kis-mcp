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
from .settings import EverythingToolSettings

Which = Callable[[str], str | None]


def everything_tool_descriptor(
    settings: EverythingToolSettings,
    *,
    which: Which = shutil.which,
) -> ToolDescriptor:
    def build() -> StdioMcpCommand:
        return StdioMcpCommand(
            executable=settings.executable,
            arguments=(str(settings.entry_point), *settings.arguments),
        )

    def readiness() -> ToolReadiness:
        details = {
            "package_name": settings.package_name,
            "package_version": settings.package_version,
            "entry_point": str(settings.entry_point),
            "test_only": True,
        }
        if not settings.enabled:
            return ToolReadiness(
                tool_id="mcp-everything",
                state=ToolState.DISABLED,
                summary="Everything MCP protocol test server is disabled.",
                details=details,
            )
        if which(settings.executable) is None:
            return ToolReadiness(
                tool_id="mcp-everything",
                state=ToolState.UNAVAILABLE,
                summary="Configured Node executable is unavailable.",
                details=details,
            )
        if not settings.entry_point.is_file():
            return ToolReadiness(
                tool_id="mcp-everything",
                state=ToolState.UNAVAILABLE,
                summary="Everything MCP local entry point is unavailable.",
                details=details,
            )
        return ToolReadiness(
            tool_id="mcp-everything",
            state=ToolState.READY,
            summary="Pinned Everything MCP protocol test server is available locally.",
            details=details,
        )

    return ToolDescriptor(
        tool_id="mcp-everything",
        display_name="MCP Everything Test Server",
        tool_kind=ToolKind.MCP_ADAPTER,
        boundary=ToolBoundary.LOCAL_PROCESS,
        authoritative_source=(
            f"{settings.source_repository}/tree/{settings.source_revision}/src/everything"
        ),
        source_revision=settings.source_revision,
        capabilities=(
            ToolCapability(
                capability_id="mcp.protocol.exercise",
                description="Exercise MCP protocol features through the upstream test server.",
                effects=("local_process",),
                operation_names=("stdio",),
            ),
        ),
        builder=build,
        readiness_probe=readiness,
        enabled=settings.enabled,
    )


__all__ = ["everything_tool_descriptor"]
