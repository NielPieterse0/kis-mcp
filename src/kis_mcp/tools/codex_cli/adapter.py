from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .settings import CodexSettings

Runner = Callable[..., subprocess.CompletedProcess[str]]


class CodexCliError(RuntimeError):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.details = dict(details or {})


class CodexCliAdapter:
    """Invoke Codex CLI only through the fixed read-only PowerShell wrapper."""

    name = "codex-cli"

    def __init__(
        self,
        settings: CodexSettings,
        *,
        runner: Runner = subprocess.run,
        pwsh_executable: str = "pwsh",
        which: Callable[[str], str | None] = shutil.which,
    ) -> None:
        self.settings = settings
        self._runner = runner
        self._pwsh_executable = pwsh_executable
        self._which = which

    def available(self) -> bool:
        return (
            self.settings.enabled
            and self.settings.script_path.is_file()
            and self._which(self._pwsh_executable) is not None
            and self._which(self.settings.executable) is not None
        )

    def review(self, project_path: Path, prompt: str) -> str:
        project = project_path.resolve()
        args = [
            self._pwsh_executable,
            "-NoProfile",
            "-File",
            str(self.settings.script_path),
            "-CodexExecutable",
            self.settings.executable,
            "-ProjectPath",
            str(project),
            "-CodexHome",
            str(self.settings.home_path),
        ]
        try:
            completed = self._runner(
                args,
                input=prompt,
                timeout=self.settings.timeout_seconds,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="strict",
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise CodexCliError(
                "CODEX_CLI_TIMEOUT",
                "Codex CLI review timed out",
                {"timeout_seconds": self.settings.timeout_seconds},
            ) from exc
        except UnicodeError as exc:
            raise CodexCliError(
                "CODEX_CLI_ENCODING_FAILED",
                "Codex CLI process text boundary failed",
                {"error_type": type(exc).__name__},
            ) from exc
        except OSError as exc:
            raise CodexCliError(
                "CODEX_CLI_START_FAILED",
                "Codex CLI wrapper could not start",
                {"error_type": type(exc).__name__},
            ) from exc
        if completed.returncode == 86:
            raise CodexCliError(
                "CODEX_CLI_MUTATION_DETECTED",
                "Codex CLI changed repository state during a read-only review",
            )
        if completed.returncode != 0:
            raise CodexCliError(
                "CODEX_CLI_PROCESS_FAILED",
                "Codex CLI review process failed",
                {"returncode": completed.returncode},
            )
        stdout = completed.stdout or ""
        if len(stdout) > self.settings.max_output_chars:
            raise CodexCliError(
                "CODEX_CLI_OUTPUT_LIMIT",
                "Codex CLI output exceeded the configured budget",
                {"max_output_chars": self.settings.max_output_chars},
            )
        messages: list[str] = []
        for line in stdout.splitlines():
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict) or event.get("type") != "item.completed":
                continue
            item = event.get("item")
            if not isinstance(item, dict) or item.get("type") != "agent_message":
                continue
            text = item.get("text")
            if isinstance(text, str) and text.strip():
                messages.append(text.strip())
        if not messages:
            raise CodexCliError(
                "CODEX_CLI_RESPONSE_INVALID",
                "Codex CLI response did not contain an agent message",
            )
        return messages[-1]


__all__ = ["CodexCliAdapter", "CodexCliError"]
