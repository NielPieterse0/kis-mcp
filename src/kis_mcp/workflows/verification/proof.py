from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ...discover.contracts import InspectProjectRequest
from ...execution.contracts import (
    ExecutionProfile,
    ExecutionRequest,
    ExecutionResult,
    ExecutionSource,
)
from ...execution.hyperv import HyperVDisposableExecutionProvider
from ...execution.settings import RunnerProfileSettings
from .contracts import VerificationResult
from .execution import (
    InspectProjectPort,
    VerificationExecutionError,
    _SUPPORTED_EXECUTABLES,
    _arguments,
    _find_declaration,
    _project_identity,
    _request_identity,
    _required,
    verification_result_from_execution,
)


@dataclass(frozen=True, slots=True)
class DisposableVerificationProofResult:
    verification: VerificationResult
    execution: ExecutionResult

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "verification": self.verification.to_json_dict(),
            "execution": self.execution.to_json_dict(),
        }


class DisposableVerificationProofService:
    """Internal proof adapter; intentionally not registered as a public Work tool."""

    def __init__(
        self,
        *,
        inspector: InspectProjectPort,
        provider: HyperVDisposableExecutionProvider,
        runner_profile: RunnerProfileSettings,
        max_evidence_chars: int = 20_000,
        max_timeout_ms: int = 300_000,
    ) -> None:
        if runner_profile.backend_id != "windows-hyperv":
            raise ValueError("disposable verification proof requires a windows-hyperv profile")
        if max_evidence_chars < 1 or max_timeout_ms < 1:
            raise ValueError("disposable verification proof limits must be positive")
        self._inspector = inspector
        self._provider = provider
        self._runner_profile = runner_profile
        self._max_evidence_chars = max_evidence_chars
        self._max_timeout_ms = max_timeout_ms

    async def run(
        self,
        *,
        project: str,
        exact_revision: str,
        verification_id: str,
        timeout_ms: int = 120_000,
    ) -> DisposableVerificationProofResult:
        project = _required(project, "project")
        verification_id = _required(verification_id, "verification_id")
        if isinstance(timeout_ms, bool) or not isinstance(timeout_ms, int) or not 1 <= timeout_ms <= self._max_timeout_ms:
            raise VerificationExecutionError(
                "VERIFICATION_TIMEOUT_INVALID",
                f"timeout_ms must be an integer from 1 to {self._max_timeout_ms}.",
            )
        source = ExecutionSource(
            project_path=project,
            revision=exact_revision,
            exact=True,
        )
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
            source=source,
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
        execution = await self._provider.execute(request)
        verification = verification_result_from_execution(
            verification_id=verification_id,
            declaration=declaration,
            verification_profile=verification_profile,
            arguments=arguments,
            execution=execution,
        )
        return DisposableVerificationProofResult(
            verification=verification,
            execution=execution,
        )


__all__ = [
    "DisposableVerificationProofResult",
    "DisposableVerificationProofService",
]
