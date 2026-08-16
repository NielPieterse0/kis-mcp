from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any, Protocol

from ...discover.contracts import InspectProjectRequest
from ...execution.contracts import (
    ExecutionProfile,
    ExecutionRequest,
    ExecutionResult,
    ExecutionSource,
)
from ...execution.local import LocalProcessExecutionProvider
from ...execution.process import Runner
from ...execution.settings import ExecutionRunnerSettings, load_execution_runner_settings
from .contracts import VerificationResult

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
        execution_settings: ExecutionRunnerSettings | None = None,
        max_evidence_chars: int = 20_000,
        max_timeout_ms: int = 300_000,
    ) -> None:
        if max_evidence_chars < 1 or max_timeout_ms < 1:
            raise ValueError("verification execution limits must be positive")
        settings = execution_settings or load_execution_runner_settings()
        runner_profile = settings.profile(settings.default_profile)
        if runner_profile.backend_id != "local-process" or not runner_profile.enabled:
            raise ValueError(
                "public verification execution requires an enabled local-process default profile"
            )
        self._inspector = inspector
        self._runner_profile = runner_profile
        self._provider = LocalProcessExecutionProvider(runner, runner_profile)
        self._max_evidence_chars = min(max_evidence_chars, settings.evidence_limit_chars)
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
        verification_profile = _required(
            str(declaration.get("profile", "")), "verification profile"
        )
        executable = _SUPPORTED_EXECUTABLES.get(verification_profile)
        if executable is None:
            raise VerificationExecutionError(
                "VERIFICATION_PROFILE_UNSUPPORTED",
                f"Verification profile {verification_profile!r} is not executable by Work.",
            )
        arguments = _arguments(declaration)
        request = ExecutionRequest(
            request_id=_request_identity(
                project, verification_id, verification_profile, arguments
            ),
            project_id=_project_identity(project),
            verification_profile_id=verification_profile,
            source=ExecutionSource(project_path=project, revision="working-tree", exact=False),
            profile=ExecutionProfile(
                profile_id=self._runner_profile.profile_id,
                backend_id=self._runner_profile.backend_id,
                image_id=self._runner_profile.image_id,
                toolchain_id=self._runner_profile.toolchain_id,
            ),
            executable=executable,
            arguments=arguments,
            timeout_ms=timeout_ms,
            evidence_limit_chars=self._max_evidence_chars,
        )
        try:
            execution = await self._provider.execute(request)
        except ValueError as exc:
            raise VerificationExecutionError(
                "VERIFICATION_EXECUTION_BACKEND_FAILED",
                str(exc),
            ) from exc
        return verification_result_from_execution(
            verification_id=verification_id,
            declaration=declaration,
            verification_profile=verification_profile,
            arguments=arguments,
            execution=execution,
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


def verification_result_from_execution(
    *,
    verification_id: str,
    declaration: Mapping[str, Any],
    verification_profile: str,
    arguments: tuple[str, ...],
    execution: ExecutionResult,
) -> VerificationResult:
    if execution.status == "passed":
        failure = "none"
    elif execution.status == "failed":
        failure = "verification_failed"
    else:
        failure = "timeout_or_incomplete"
    evidence = execution.evidence.stdout
    if execution.evidence.stderr:
        evidence = "\n".join(item for item in (evidence, execution.evidence.stderr) if item)
    return VerificationResult(
        verification_id=verification_id,
        title=_required(str(declaration.get("title", "")), "verification title"),
        category=_required(str(declaration.get("category", "")), "verification category"),
        source_path=_required(str(declaration.get("source_path", "")), "verification source path"),
        profile=verification_profile,
        arguments=arguments,
        command_identity=_command_identity(verification_profile, arguments),
        status=execution.status,
        exit_code=execution.exit_code,
        duration_ms=execution.duration_ms,
        evidence=evidence,
        failure_classification=failure,
        truncated=execution.evidence.truncated,
    )


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


def _command_identity(profile: str, arguments: tuple[str, ...]) -> str:
    payload = json.dumps(
        {"profile": profile, "arguments": list(arguments)},
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _request_identity(
    project: str,
    verification_id: str,
    profile: str,
    arguments: tuple[str, ...],
) -> str:
    payload = json.dumps(
        {
            "project": project,
            "verification_id": verification_id,
            "profile": profile,
            "arguments": list(arguments),
        },
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"verification-{hashlib.sha256(payload).hexdigest()[:24]}"


def _project_identity(project: str) -> str:
    digest = hashlib.sha256(project.encode("utf-8")).hexdigest()[:20]
    return f"project-{digest}"


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
