from __future__ import annotations

import json
import re
from collections.abc import Awaitable, Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from .contracts import AgentValidationResult
from .settings import AgnixValidationSettings

Runner = Callable[[str, dict[str, Any]], Awaitable[Any]]
_EXIT_MARKER = re.compile(r"(?m)^__KIS_AGNIX_EXIT_CODE=(-?\d+)\s*$")
_FILE_LIMIT_ERROR = re.compile(
    r"Too many files to validate:\s*(\d+)\s+files found,\s*limit is\s*(\d+)",
    re.IGNORECASE,
)
_APPLICATION_CONTROL_ERROR = re.compile(
    r"(?:Application Control policy has blocked|app has been blocked|Windows cannot confirm who published)",
    re.IGNORECASE,
)


class AgentValidationError(ValueError):
    def __init__(self, code: str, reason: str) -> None:
        self.code = code
        self.reason = reason
        super().__init__(f"{code}: {reason}")


class AgentValidationService:
    def __init__(self, *, boundary: Path, settings: AgnixValidationSettings, runner: Runner) -> None:
        self._boundary = boundary.resolve()
        self._settings = settings
        self._runner = runner

    async def validate(self, *, project: str, target: str = "generic", strict: bool = False, max_files: int | None = None) -> AgentValidationResult:
        root = self._project(project)
        target = self._target(target)
        limit = self._max_files(max_files)
        binary = self._settings.binary_path
        if not binary.is_file():
            raise AgentValidationError("AGNIX_UNAVAILABLE", f"Pinned agnix binary is unavailable at {binary}.")
        command = self._command(root, binary, target, strict, limit)
        result = await self._runner("start_process", {"command": command, "timeout_ms": self._settings.timeout_ms, "shell": "powershell.exe"})
        text = _result_text(result)
        exit_code = _exit_code(text)
        if exit_code is None:
            pid = _result_pid(result)
            if pid is not None:
                follow = await self._runner("read_process_output", {"pid": pid, "timeout_ms": self._settings.timeout_ms, "offset": 0, "length": 1000})
                text = "\n".join(item for item in (text, _result_text(follow)) if item)
                exit_code = _exit_code(text)
        payload_text = _EXIT_MARKER.sub("", text).strip()
        if len(payload_text) > self._settings.max_output_chars:
            raise AgentValidationError("AGNIX_OUTPUT_LIMIT", "agnix output exceeded the configured budget.")
        if exit_code is None and _APPLICATION_CONTROL_ERROR.search(payload_text):
            raise AgentValidationError(
                "AGNIX_APPLICATION_CONTROL_BLOCKED",
                "Windows Application Control blocked the agnix launch path; reinstall through the governed Defender-safe runtime bootstrap.",
            )
        if exit_code is None:
            raise AgentValidationError("AGNIX_INCOMPLETE", "agnix did not produce a completed process result.")
        file_limit = _FILE_LIMIT_ERROR.search(payload_text)
        if file_limit is not None:
            found, limit_value = (int(value) for value in file_limit.groups())
            raise AgentValidationError(
                "AGNIX_FILE_LIMIT_EXCEEDED",
                f"agnix found {found} files, exceeding the requested limit {limit_value}.",
            )
        payload = _json_payload(payload_text)
        if payload is None:
            raise AgentValidationError("AGNIX_OUTPUT_INVALID", "agnix did not return valid JSON output.")
        if payload.get("version") != self._settings.version:
            raise AgentValidationError("AGNIX_VERSION_MISMATCH", f"Expected agnix {self._settings.version}, got {payload.get('version')!r}.")
        diagnostics = payload.get("diagnostics", [])
        if not isinstance(diagnostics, list) or any(not isinstance(item, dict) for item in diagnostics):
            raise AgentValidationError("AGNIX_OUTPUT_INVALID", "agnix diagnostics are not a JSON object list.")
        truncated = len(diagnostics) > self._settings.max_findings
        bounded = tuple(dict(item) for item in diagnostics[: self._settings.max_findings])
        summary = payload.get("summary", {}) if isinstance(payload.get("summary"), dict) else {}
        if exit_code not in (0, 1):
            raise AgentValidationError("AGNIX_PROCESS_FAILED", f"agnix exited with code {exit_code}.")
        return AgentValidationResult(
            project=str(root), target=target, strict=strict, max_files=limit,
            version=self._settings.version, files_checked=_nonnegative_int(payload.get("files_checked"), "files_checked"),
            diagnostics=bounded, errors=_nonnegative_int(summary.get("errors", 0), "errors"),
            warnings=_nonnegative_int(summary.get("warnings", 0), "warnings"), info=_nonnegative_int(summary.get("info", 0), "info"),
            truncated=truncated,
        )

    def _project(self, value: str) -> Path:
        if not isinstance(value, str) or not value.strip():
            raise AgentValidationError("AGNIX_REQUEST_INVALID", "project must be a non-empty string.")
        path = Path(value).resolve()
        try:
            path.relative_to(self._boundary)
        except ValueError as exc:
            raise AgentValidationError("AGNIX_PROJECT_OUTSIDE_BOUNDARY", f"project must resolve beneath {self._boundary}.") from exc
        if not path.is_dir():
            raise AgentValidationError("AGNIX_PROJECT_INVALID", "project must resolve to an existing directory.")
        return path

    def _target(self, value: str) -> str:
        if value not in self._settings.targets:
            raise AgentValidationError("AGNIX_TARGET_INVALID", f"target must be one of {', '.join(self._settings.targets)}.")
        return value

    def _max_files(self, value: int | None) -> int:
        if value is None:
            return self._settings.default_max_files
        if isinstance(value, bool) or not isinstance(value, int) or value < 1 or value > self._settings.max_files:
            raise AgentValidationError("AGNIX_MAX_FILES_INVALID", f"max_files must be from 1 through {self._settings.max_files}.")
        return value

    def _command(self, root: Path, binary: Path, target: str, strict: bool, max_files: int) -> str:
        flags = ["--format", "json", "--target", target, "--max-files", str(max_files)]
        if strict:
            flags.append("--strict")
        tokens = " ".join(
            _ps_quote(item)
            for item in (
                "wsl.exe",
                "--distribution",
                self._settings.wsl_distribution,
                "--cd",
                _wsl_path(root),
                "--exec",
                _wsl_path(binary),
                *flags,
                ".",
            )
        )
        return (
            f"& {tokens}; $kisCode = $LASTEXITCODE; "
            "Write-Output \"__KIS_AGNIX_EXIT_CODE=$kisCode\"; exit $kisCode"
        )


def _wsl_path(path: Path) -> str:
    resolved = path.resolve()
    drive = resolved.drive.rstrip(":").lower()
    if len(drive) != 1 or not drive.isalpha():
        raise AgentValidationError("AGNIX_WSL_PATH_INVALID", f"Cannot map Windows path into WSL: {resolved}.")
    tail = resolved.as_posix().split(":", 1)[1].lstrip("/")
    return f"/mnt/{drive}/{tail}"


def _ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _json_payload(text: str) -> dict[str, Any] | None:
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        return None
    try:
        value = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _nonnegative_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise AgentValidationError("AGNIX_OUTPUT_INVALID", f"agnix {label} is invalid.")
    return value


def _result_text(result: Any) -> str:
    parts: list[str] = []

    def visit(value: Any, depth: int) -> None:
        if value is None or depth > 4:
            return
        if isinstance(value, str):
            parts.append(value)
            return
        if isinstance(value, Mapping):
            for key in ("text", "output", "content", "structured_content", "result"):
                if key in value:
                    visit(value[key], depth + 1)
            return
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            for item in value:
                visit(item, depth + 1)
            return
        for attribute in ("text", "content", "structured_content", "result"):
            if hasattr(value, attribute):
                visit(getattr(value, attribute), depth + 1)

    visit(result, 0)
    return "\n".join(part for part in parts if part).strip()


def _result_pid(result: Any) -> int | None:
    if isinstance(result, Mapping):
        pid = result.get("pid")
        if isinstance(pid, int) and not isinstance(pid, bool) and pid > 0:
            return pid
        for value in result.values():
            found = _result_pid(value)
            if found is not None:
                return found
    if isinstance(result, Sequence) and not isinstance(result, (str, bytes, bytearray)):
        for value in result:
            found = _result_pid(value)
            if found is not None:
                return found
    if hasattr(result, "pid"):
        pid = getattr(result, "pid")
        if isinstance(pid, int) and not isinstance(pid, bool) and pid > 0:
            return pid
    for attribute in ("content", "structured_content", "result"):
        if hasattr(result, attribute):
            found = _result_pid(getattr(result, attribute))
            if found is not None:
                return found
    return None


def _exit_code(text: str) -> int | None:
    matches = _EXIT_MARKER.findall(text)
    return int(matches[-1]) if matches else None


__all__ = ["AgentValidationError", "AgentValidationService", "Runner"]
