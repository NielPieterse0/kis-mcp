from __future__ import annotations

import os
import re
import shutil
import subprocess
from collections.abc import Callable

from ..contracts import (
    ToolBoundary,
    ToolCapability,
    ToolDescriptor,
    ToolKind,
    ToolReadiness,
    ToolState,
)
from ..registry import ToolRegistry
from .settings import CodexSettings
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
                summary="The pinned Codex CLI is not installed.",
                details={"executable": settings.executable},
            )
        environment = os.environ.copy()
        environment["CODEX_HOME"] = str(settings.home_path)
        for name in ("OPENAI_API_KEY", "OPENAI_BASE_URL", "CODEX_ACCESS_TOKEN"):
            environment.pop(name, None)
        try:
            version_result = runner(
                [settings.executable, "--version"],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
                env=environment,
            )
        except (OSError, subprocess.TimeoutExpired):
            return ToolReadiness(
                tool_id="codex-cli",
                state=ToolState.DEGRADED,
                summary="The pinned Codex CLI could not be inspected.",
                details={"executable": settings.executable},
            )
        match = re.search(r"(\d+\.\d+\.\d+)", version_result.stdout or "")
        reported_version = match.group(1) if match else "unknown"
        if version_result.returncode != 0 or reported_version != settings.expected_version:
            return ToolReadiness(
                tool_id="codex-cli",
                state=ToolState.DEGRADED,
                summary="The installed Codex CLI version does not match the configured pin.",
                details={
                    "expected_version": settings.expected_version,
                    "reported_version": reported_version,
                },
            )
        try:
            auth_result = runner(
                [settings.executable, "login", "status"],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
                env=environment,
            )
        except (OSError, subprocess.TimeoutExpired):
            auth_result = subprocess.CompletedProcess([], 1, stdout="", stderr="")
        auth_status = "\n".join(
            part for part in (auth_result.stdout, auth_result.stderr) if part
        ).casefold()
        authenticated = (
            auth_result.returncode == 0
            and "logged in using chatgpt" in auth_status
        )
        if not authenticated:
            return ToolReadiness(
                tool_id="codex-cli",
                state=ToolState.DEGRADED,
                summary="Codex CLI is installed but ChatGPT authentication is not verified.",
                details={"version": reported_version, "authentication": "not-chatgpt"},
            )
        return ToolReadiness(
            tool_id="codex-cli",
            state=ToolState.READY,
            summary="Pinned Codex CLI and ChatGPT authentication are ready.",
            details={"version": reported_version, "authentication": "chatgpt"},
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
