from __future__ import annotations

from .contracts import (
    CleanupDisposition,
    ExecutionEvidence,
    ExecutionLifecycleState,
    ExecutionReadiness,
    ExecutionRequest,
    ExecutionResult,
    ReadinessStatus,
)
from .process import Runner, clean_process_text, run_nested_process
from .settings import RunnerProfileSettings


class LocalProcessExecutionProvider:
    backend_id = "local-process"

    def __init__(self, runner: Runner, profile: RunnerProfileSettings) -> None:
        if profile.backend_id != self.backend_id:
            raise ValueError("local execution provider requires a local-process runner profile")
        self._runner = runner
        self._profile = profile

    async def readiness(self) -> ExecutionReadiness:
        return ExecutionReadiness(
            backend_id=self.backend_id,
            status=ReadinessStatus.READY,
            reason="local process execution is available through the configured Work runner",
        )

    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        if (
            request.profile.backend_id != self.backend_id
            or request.profile.profile_id != self._profile.profile_id
            or request.profile.image_id != self._profile.image_id
            or request.profile.toolchain_id != self._profile.toolchain_id
        ):
            return ExecutionResult(
                request_id=request.request_id,
                backend_id=self.backend_id,
                status="incomplete",
                exit_code=None,
                duration_ms=0,
                source_revision=request.source.revision,
                image_id=self._profile.image_id,
                toolchain_id=self._profile.toolchain_id,
                cleanup=CleanupDisposition.NOT_REQUIRED,
                evidence=ExecutionEvidence(),
                failure_classification="profile_identity_mismatch",
                lifecycle=(
                    ExecutionLifecycleState.REQUESTED,
                    ExecutionLifecycleState.INCOMPLETE,
                ),
            )
        command = _process_command(request)
        outcome = await run_nested_process(
            self._runner,
            command=command,
            timeout_ms=request.timeout_ms,
        )
        evidence, truncated = clean_process_text(
            outcome.text,
            request.evidence_limit_chars,
        )
        if outcome.exit_code is None:
            status = "incomplete"
            failure = "timeout_or_incomplete"
        elif outcome.exit_code == 0:
            status = "passed"
            failure = "none"
        else:
            status = "failed"
            failure = "execution_failed"
        return ExecutionResult(
            request_id=request.request_id,
            backend_id=self.backend_id,
            status=status,
            exit_code=outcome.exit_code,
            duration_ms=outcome.duration_ms,
            source_revision=request.source.revision,
            image_id=self._profile.image_id,
            toolchain_id=self._profile.toolchain_id,
            cleanup=CleanupDisposition.NOT_REQUIRED,
            evidence=ExecutionEvidence(stdout=evidence, truncated=truncated),
            failure_classification=failure,
            lifecycle=(
                ExecutionLifecycleState.REQUESTED,
                ExecutionLifecycleState.EXECUTING,
                ExecutionLifecycleState.COMPLETED
                if status != "incomplete"
                else ExecutionLifecycleState.INCOMPLETE,
            ),
        )


def _process_command(request: ExecutionRequest) -> str:
    tokens = " ".join(
        _ps_quote(item) for item in (request.executable, *request.arguments)
    )
    return (
        f"Set-Location -LiteralPath {_ps_quote(request.source.project_path)}; "
        f"& {tokens}; "
        "$kisCode = $LASTEXITCODE; "
        'Write-Output "__KIS_VERIFICATION_EXIT_CODE=$kisCode"; '
        "exit $kisCode"
    )


def _ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


__all__ = ["LocalProcessExecutionProvider"]
