from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable

from .. import (
    ToolBoundary,
    ToolCapability,
    ToolDescriptor,
    ToolKind,
    ToolReadiness,
    ToolRegistry,
    ToolState,
)
from ...workflows.code_review.settings import CodexSettings
from .adapter import CodexCliAdapter

Which = Callable[[str], str | None]
Runner = Callable[..., subprocess.CompletedProcess[str]]


def codex_tool_descriptor(
    settings: CodexSettings,
    *,
    which: Which = shutil.which,
    runner: Runner = subprocess.run,
    pwsh_executable: str = "pwsh",
) -> ToolDescriptor:
    """Describe the optional Codex CLI reviewer without invoking it."""

    def readiness() -> ToolReadiness:
        if not settings.enabled:
            return ToolReadiness(
                tool_id="codex-cli",
                state=ToolState.DISABLED,
                summary="Codex CLI is disabled by agent settings.",
            )
        if not settings.script_path.is_file():
            return ToolReadiness(
                tool_id="codex-cli",
                state=ToolState.UNAVAILABLE,
                summary="The Codex CLI wrapper script is unavailable.",
                details={"script_configured": False},
            )
        if which(pwsh_executable) is None:
            return ToolReadiness(
                tool_id="codex-cli",
                state=ToolState.UNAVAILABLE,
                summary="PowerShell is required for the Codex CLI wrapper.",
                details={"executable": pwsh_executable},
            )
        if which(settings.executable) is None:
            return ToolReadiness(
                tool_id="codex-cli",
                state=ToolState.DEGRADED,
                summary="Codex CLI is ready for installation or PATH configuration.",
                details={"executable": settings.executable},
            )
        return ToolReadiness(
            tool_id="codex-cli",
            state=ToolState.READY,
            summary="Codex CLI executable and read-only wrapper are available.",
            details={"authentication": "unverified"},
        )

    def build() -> CodexCliAdapter:
        return CodexCliAdapter(
            settings,
            runner=runner,
            pwsh_executable=pwsh_executable,
            which=which,
        )

    return ToolDescriptor(
        tool_id="codex-cli",
        display_name="Codex CLI",
        tool_kind=ToolKind.LOCAL_EXECUTABLE,
        boundary=ToolBoundary.LOCAL_PROCESS,
        authoritative_source="https://github.com/openai/codex",
        source_revision="codex-exec-json-v1",
        capabilities=(
            ToolCapability(
                capability_id="code.review.codex-cli",
                description="Run one bounded advisory code review through Codex CLI.",
                effects=("local_read", "external_network"),
                operation_names=("review_change_with_agent",),
            ),
        ),
        builder=build,
        readiness_probe=readiness,
        enabled=settings.enabled,
    )


def register_codex_tool(
    registry: ToolRegistry,
    *,
    settings: CodexSettings,
    which: Which = shutil.which,
    runner: Runner = subprocess.run,
    pwsh_executable: str = "pwsh",
) -> ToolDescriptor:
    return registry.register(
        codex_tool_descriptor(
            settings,
            which=which,
            runner=runner,
            pwsh_executable=pwsh_executable,
        )
    )


__all__ = ["codex_tool_descriptor", "register_codex_tool"]
