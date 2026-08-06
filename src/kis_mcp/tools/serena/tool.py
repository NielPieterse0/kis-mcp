from __future__ import annotations

from collections.abc import Mapping

from ..contracts import (
    ToolBoundary,
    ToolCapability,
    ToolDescriptor,
    ToolKind,
    ToolReadiness,
    ToolState,
)
from .adapter import ProxyFactory, SerenaAdapter
from .settings import SerenaSettings

_EFFECT_OPERATIONS = (
    "delete_memory",
    "edit_memory",
    "execute_shell_command",
    "insert_after_symbol",
    "insert_before_symbol",
    "rename_memory",
    "rename_symbol",
    "replace_content",
    "replace_symbol_body",
    "write_memory",
)


def serena_tool_descriptor(
    settings: SerenaSettings,
    *,
    environment: Mapping[str, str] | None = None,
    proxy_factory: ProxyFactory | None = None,
) -> ToolDescriptor:
    def build() -> SerenaAdapter:
        kwargs: dict[str, object] = {}
        if environment is not None:
            kwargs["environment"] = environment
        if proxy_factory is not None:
            kwargs["proxy_factory"] = proxy_factory
        return SerenaAdapter(settings, **kwargs)

    def readiness() -> ToolReadiness:
        managed_roots = (
            settings.install_root,
            settings.home_root,
            settings.config_root,
            settings.cache_root,
            settings.log_root,
            settings.temp_root,
            settings.language_server_root,
            settings.global_memory_root,
        )
        details = {
            "package_name": settings.package_name,
            "package_version": settings.package_version,
            "source_revision": settings.source_revision,
            "executable": str(settings.executable),
            "provider_managed_storage_inside_boundary": True,
            "managed_roots": [str(path) for path in managed_roots],
            "effect_operations": list(_EFFECT_OPERATIONS),
            "usage_reporting": False,
            "web_dashboard": False,
        }
        if not settings.enabled:
            return ToolReadiness(
                tool_id="serena-mcp",
                state=ToolState.DISABLED,
                summary="Serena MCP is disabled.",
                details=details,
            )
        if not settings.executable.is_file():
            return ToolReadiness(
                tool_id="serena-mcp",
                state=ToolState.UNAVAILABLE,
                summary="Pinned Serena local executable is unavailable.",
                details=details,
            )
        missing_roots = [str(path) for path in managed_roots if not path.exists()]
        if missing_roots:
            details["missing_roots"] = missing_roots
            return ToolReadiness(
                tool_id="serena-mcp",
                state=ToolState.DEGRADED,
                summary="Serena executable is present but managed storage is incomplete.",
                details=details,
            )
        return ToolReadiness(
            tool_id="serena-mcp",
            state=ToolState.READY,
            summary="Pinned Serena MCP runtime and managed storage are available locally.",
            details=details,
        )

    return ToolDescriptor(
        tool_id="serena-mcp",
        display_name="Serena MCP",
        tool_kind=ToolKind.MCP_ADAPTER,
        boundary=ToolBoundary.LOCAL_PROCESS,
        authoritative_source=(
            f"{settings.source_repository}/tree/{settings.source_revision}"
        ),
        source_revision=settings.source_revision,
        capabilities=(
            ToolCapability(
                capability_id="code.semantic.serena",
                description="Provide semantic code navigation and bounded mutation through Serena.",
                effects=("local_process", "read", "write", "delete", "shell"),
                operation_names=_EFFECT_OPERATIONS,
            ),
        ),
        builder=build,
        readiness_probe=readiness,
        enabled=settings.enabled,
    )


__all__ = ["serena_tool_descriptor"]