from __future__ import annotations

import re
import shutil
import subprocess
from collections.abc import Callable, Mapping

from ..contracts import (
    ToolBoundary,
    ToolCapability,
    ToolDescriptor,
    ToolKind,
    ToolReadiness,
    ToolState,
)
from .adapter import Context7Adapter, ProxyFactory
from .settings import Context7Settings

Which = Callable[[str], str | None]
NodeVersion = Callable[[str], str]
_VERSION = re.compile(r"v?(\d+)\.(\d+)\.(\d+)")


def _node_version(executable: str) -> str:
    completed = subprocess.run(
        [executable, "--version"],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return completed.stdout.strip() if completed.returncode == 0 else ""


def _version_tuple(value: str) -> tuple[int, int, int] | None:
    match = _VERSION.fullmatch(value.strip())
    return tuple(int(item) for item in match.groups()) if match else None


def context7_tool_descriptor(
    settings: Context7Settings,
    *,
    which: Which = shutil.which,
    node_version: NodeVersion = _node_version,
    environment: Mapping[str, str] | None = None,
    proxy_factory: ProxyFactory | None = None,
) -> ToolDescriptor:
    def build() -> Context7Adapter:
        kwargs: dict[str, object] = {}
        if environment is not None:
            kwargs["environment"] = environment
        if proxy_factory is not None:
            kwargs["proxy_factory"] = proxy_factory
        return Context7Adapter(settings, **kwargs)

    def readiness() -> ToolReadiness:
        details = {
            "package_name": settings.package_name,
            "package_version": settings.package_version,
            "source_revision": settings.source_revision,
            "entry_point": str(settings.entry_point),
            "environment_names": list(settings.environment_names),
            "operations": ["resolve-library-id", "query-docs"],
        }
        if not settings.enabled:
            return ToolReadiness(
                tool_id="context7-mcp",
                state=ToolState.DISABLED,
                summary="Context7 MCP is disabled.",
                details=details,
            )
        resolved = which(settings.executable)
        if resolved is None or not settings.entry_point.is_file():
            return ToolReadiness(
                tool_id="context7-mcp",
                state=ToolState.UNAVAILABLE,
                summary="Pinned Context7 local runtime is unavailable.",
                details=details,
            )
        actual = _version_tuple(node_version(resolved))
        minimum = _version_tuple(settings.node_minimum_version)
        if actual is None or minimum is None or actual < minimum:
            return ToolReadiness(
                tool_id="context7-mcp",
                state=ToolState.UNAVAILABLE,
                summary="Node.js does not satisfy the pinned Context7 minimum version.",
                details=details,
            )
        return ToolReadiness(
            tool_id="context7-mcp",
            state=ToolState.READY,
            summary="Pinned Context7 MCP runtime is available locally.",
            details=details,
        )

    return ToolDescriptor(
        tool_id="context7-mcp",
        display_name="Context7 MCP",
        tool_kind=ToolKind.MCP_ADAPTER,
        boundary=ToolBoundary.APPROVED_EXTERNAL_SERVICE,
        authoritative_source=(
            f"{settings.source_repository}/tree/{settings.source_revision}"
        ),
        source_revision=settings.source_revision,
        capabilities=(
            ToolCapability(
                capability_id="documentation.context7",
                description="Resolve libraries and query current documentation through Context7.",
                effects=("external_network", "read_only"),
                operation_names=("resolve-library-id", "query-docs"),
            ),
        ),
        builder=build,
        readiness_probe=readiness,
        enabled=settings.enabled,
    )


__all__ = ["context7_tool_descriptor"]