from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..contracts import (
    ToolBoundary,
    ToolCapability,
    ToolDescriptor,
    ToolKind,
    ToolReadiness,
    ToolState,
)
from .settings import McpSpecSettings


@dataclass(frozen=True, slots=True)
class McpSpecPluginSource:
    source_repository: str
    source_revision: str
    plugin_path: str
    plugin_root: Path | None

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "source_repository": self.source_repository,
            "source_revision": self.source_revision,
            "plugin_path": self.plugin_path,
            "plugin_root": None if self.plugin_root is None else str(self.plugin_root),
        }


def mcp_spec_tool_descriptor(settings: McpSpecSettings) -> ToolDescriptor:
    plugin_root = (
        None
        if settings.local_checkout is None
        else settings.local_checkout / Path(settings.plugin_path)
    )

    def build() -> McpSpecPluginSource:
        return McpSpecPluginSource(
            source_repository=settings.source_repository,
            source_revision=settings.source_revision,
            plugin_path=settings.plugin_path,
            plugin_root=plugin_root,
        )

    def readiness() -> ToolReadiness:
        details = {
            "plugin_path": settings.plugin_path,
            "source_revision": settings.source_revision,
        }
        if not settings.enabled:
            return ToolReadiness(
                tool_id="mcp-spec-plugin",
                state=ToolState.DISABLED,
                summary="MCP Spec plugin metadata is disabled.",
                details=details,
            )
        if plugin_root is None:
            return ToolReadiness(
                tool_id="mcp-spec-plugin",
                state=ToolState.DEGRADED,
                summary="MCP Spec source is pinned but no local checkout is configured.",
                details=details,
            )
        if not plugin_root.is_dir():
            return ToolReadiness(
                tool_id="mcp-spec-plugin",
                state=ToolState.UNAVAILABLE,
                summary="Configured MCP Spec plugin path is unavailable.",
                details={**details, "plugin_root": str(plugin_root)},
            )
        return ToolReadiness(
            tool_id="mcp-spec-plugin",
            state=ToolState.READY,
            summary="Pinned MCP Spec plugin source is available locally.",
            details={**details, "plugin_root": str(plugin_root)},
        )

    return ToolDescriptor(
        tool_id="mcp-spec-plugin",
        display_name="MCP Spec Plugin",
        tool_kind=ToolKind.PLATFORM_INTERNAL,
        boundary=ToolBoundary.LOCAL_READ_ONLY,
        authoritative_source=(
            f"{settings.source_repository}/tree/{settings.source_revision}/"
            f"{settings.plugin_path}"
        ),
        source_revision=settings.source_revision,
        capabilities=(
            ToolCapability(
                capability_id="mcp.spec.research",
                description=(
                    "Use the pinned upstream MCP specification research and SEP drafting "
                    "plugin source."
                ),
                effects=("local_read",),
                operation_names=("draft_sep", "search_mcp_github"),
            ),
        ),
        builder=build,
        readiness_probe=readiness,
        enabled=settings.enabled,
    )


__all__ = ["McpSpecPluginSource", "mcp_spec_tool_descriptor"]
