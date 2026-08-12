from __future__ import annotations

import hashlib
import json
import re
import time
from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Any, Protocol

from ...discover.contracts import InspectProjectRequest
from .contracts import VerificationResult

Runner = Callable[[str, dict[str, Any]], Awaitable[Any]]
_EXIT_MARKER = re.compile(r"(?m)^__KIS_VERIFICATION_EXIT_CODE=(-?\d+)\s*$")
_SUPPORTED_EXECUTABLES = {
    "python": "python",
    "uv": "uv",
    "npm": "npm",
    "powershell_verify": "pwsh",
}
SUPPORTED_VERIFICATION_PROFILES = frozenset(_SUPPORTED_EXECUTABLES)


class InspectProjectPort(Protocol):
    def inspect(self, request: InspectProjectRequest) -> Any: ...


class VerificationExecutionError(ValueError):
    def __init__(self, code: str, reason: str) -> None:
        self.code = code
        self.reason = reason
        super().__init__(f"{code}: {reason}")


class VerificationExecutionService:
    def __init__(
        self,
        *,
        inspector: InspectProjectPort,
        runner: Runner,
        max_evidence_chars: int = 20_000,
        max_timeout_ms: int = 300_000,
    ) -> None:
        if max_evidence_chars < 1 or max_timeout_ms < 1:
            raise ValueError("verification execution limits must be positive")
        self._inspector = inspector
        self._runner = runner
        self._max_evidence_chars = max_evidence_chars
        self._max_timeout_ms = max_timeout_ms

    async def run(
        self,
        *,
        project: str,
        verification_id: str,
        timeout_ms: int = 120_000,
    ) -> VerificationResult:
        project = _required(project, "project")
        verification_id = _required(verification_id, "verification_id")
        timeout_ms = self._bounded_timeout(timeout_ms)
        inspection = self._inspector.inspect(InspectProjectRequest(path=project))
        declaration = _find_declaration(inspection.verification, verification_id)
        profile = _required(str(declaration.get("profile", "")), "verification profile")
        executable = _SUPPORTED_EXECUTABLES.get(profile)
        if executable is None:
            raise VerificationExecutionError(
                "VERIFICATION_PROFILE_UNSUPPORTED",
                f"Verification profile {profile!r} is not executable by Work.",
            )
        arguments = _arguments(declaration)
        command = _process_command(project, executable, arguments)
        started = time.perf_counter()
        result = await self._runner(
            "start_process",
            {
                "command": command,
                "timeout_ms": timeout_ms,
                "shell": "powershell.exe",
            },
        )
        text = _result_text(result)
        exit_code = _exit_code(text)
        if exit_code is None:
            pid = _result_pid(result)
            if pid is not None:
                follow_up = await self._runner(
                    "read_process_output",
                    {
                        "pid": pid,
                        "timeout_ms": timeout_ms,
                        "offset": 0,
                        "length": 200,
                    },
                )
                follow_text = _result_text(follow_up)
                text = "\n".join(item for item in (text, follow_text) if item)
                exit_code = _exit_code(text)
        duration_ms = max(0, round((time.perf_counter() - started) * 1000))
        evidence, truncated = _bounded_evidence(text, self._max_evidence_chars)
        if exit_code is None:
            status = "incomplete"
            failure = "timeout_or_incomplete"
        elif exit_code == 0:
            status = "passed"
            failure = "none"
        else:
            status = "failed"
            failure = "verification_failed"
        return VerificationResult(
            verification_id=verification_id,
            title=_required(str(declaration.get("title", "")), "verification title"),
            category=_required(str(declaration.get("category", "")), "verification category"),
            source_path=_required(str(declaration.get("source_path", "")), "verification source path"),
            profile=profile,
            arguments=arguments,
            command_identity=_command_identity(profile, arguments),
            status=status,
            exit_code=exit_code,
            duration_ms=duration_ms,
            evidence=evidence,
            failure_classification=failure,
            truncated=truncated,
        )

    def _bounded_timeout(self, timeout_ms: int) -> int:
        if isinstance(timeout_ms, bool) or not isinstance(timeout_ms, int) or timeout_ms < 1:
            raise VerificationExecutionError(
                "VERIFICATION_TIMEOUT_INVALID",
                "timeout_ms must be a positive integer.",
            )
        if timeout_ms > self._max_timeout_ms:
            raise VerificationExecutionError(
                "VERIFICATION_TIMEOUT_INVALID",
                f"timeout_ms exceeds the maximum {self._max_timeout_ms}.",
            )
        return timeout_ms


def _find_declaration(
    verification: Mapping[str, Any], verification_id: str
) -> Mapping[str, Any]:
    declarations = verification.get("declarations", ())
    if not isinstance(declarations, Sequence) or isinstance(
        declarations, (str, bytes, bytearray)
    ):
        declarations = ()
    for item in declarations:
        if isinstance(item, Mapping) and item.get("id") == verification_id:
            return item
    raise VerificationExecutionError(
        "VERIFICATION_ID_UNKNOWN",
        f"Verification ID {verification_id!r} was not discovered for this project.",
    )


def _arguments(declaration: Mapping[str, Any]) -> tuple[str, ...]:
    raw = declaration.get("arguments", ())
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes, bytearray)):
        raise VerificationExecutionError(
            "VERIFICATION_DECLARATION_INVALID",
            "Discovered verification arguments are not a sequence.",
        )
    values: list[str] = []
    for item in raw:
        if not isinstance(item, str) or not item:
            raise VerificationExecutionError(
                "VERIFICATION_DECLARATION_INVALID",
                "Discovered verification arguments must be non-empty strings.",
            )
        values.append(item)
    return tuple(values)


def _process_command(
    project: str,
    executable: str,
    arguments: tuple[str, ...],
) -> str:
    tokens = " ".join(_ps_quote(item) for item in (executable, *arguments))
    return (
        f"Set-Location -LiteralPath {_ps_quote(project)}; "
        f"& {tokens}; "
        "$kisCode = $LASTEXITCODE; "
        'Write-Output "__KIS_VERIFICATION_EXIT_CODE=$kisCode"; '
        "exit $kisCode"
    )


def _ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _command_identity(profile: str, arguments: tuple[str, ...]) -> str:
    payload = json.dumps(
        {"profile": profile, "arguments": list(arguments)},
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _result_text(result: Any) -> str:
    parts: list[str] = []
    seen: set[int] = set()

    def visit(value: Any, depth: int) -> None:
        if value is None or depth > 4:
            return
        if not isinstance(value, (str, int, float, bool)):
            identity = id(value)
            if identity in seen:
                return
            seen.add(identity)
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
    seen: set[int] = set()

    def visit(value: Any, depth: int) -> int | None:
        if value is None or depth > 4:
            return None
        if not isinstance(value, (str, int, float, bool)):
            identity = id(value)
            if identity in seen:
                return None
            seen.add(identity)
        if isinstance(value, Mapping):
            pid = value.get("pid")
            if isinstance(pid, int) and not isinstance(pid, bool) and pid > 0:
                return pid
            for nested in value.values():
                found = visit(nested, depth + 1)
                if found is not None:
                    return found
            return None
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            for nested in value:
                found = visit(nested, depth + 1)
                if found is not None:
                    return found
            return None
        for attribute in ("pid", "content", "structured_content", "result"):
            if hasattr(value, attribute):
                candidate = getattr(value, attribute)
                if attribute == "pid" and isinstance(candidate, int) and candidate > 0:
                    return candidate
                found = visit(candidate, depth + 1)
                if found is not None:
                    return found
        return None

    return visit(result, 0)


def _exit_code(text: str) -> int | None:
    matches = _EXIT_MARKER.findall(text)
    return int(matches[-1]) if matches else None


def _bounded_evidence(text: str, max_chars: int) -> tuple[str, bool]:
    cleaned = _EXIT_MARKER.sub("", text).strip()
    if len(cleaned) <= max_chars:
        return cleaned, False
    head = max_chars // 2
    tail = max_chars - head
    return (
        f"{cleaned[:head]}\n... [verification evidence truncated] ...\n{cleaned[-tail:]}",
        True,
    )


def _required(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise VerificationExecutionError(
            "VERIFICATION_REQUEST_INVALID",
            f"{label} must be a non-empty string.",
        )
    return value.strip()


__all__ = [
    "InspectProjectPort",
    "Runner",
    "SUPPORTED_VERIFICATION_PROFILES",
    "VerificationExecutionError",
    "VerificationExecutionService",
]
