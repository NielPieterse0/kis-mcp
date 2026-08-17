from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from .contracts import (
    CleanupDisposition,
    ExecutionEvidence,
    ExecutionLifecycleState,
    ExecutionReadiness,
    ExecutionRequest,
    ExecutionResult,
    ReadinessStatus,
)
from .local_receipt import write_exact_receipt
from .local_state import (
    LocalExactSource,
    LocalSourceError,
    materialize_exact_source,
    update_run_state,
)
from .process import Runner, clean_process_text, run_nested_process
from .settings import RunnerProfileSettings
from .worker import WORKER_RESULT_NAME

_SOURCE_REVISION_MARKER = "__KIS_SOURCE_REVISION="
_SOURCE_TREE_MARKER = "__KIS_SOURCE_TREE="


class LocalProcessExecutionProvider:
    backend_id = "local-process"

    def __init__(self, runner: Runner, profile: RunnerProfileSettings) -> None:
        if profile.backend_id != self.backend_id or profile.local is None:
            raise ValueError("local execution provider requires local-process settings")
        self._runner = runner
        self._profile = profile
        self._local = profile.local
        self._prepared: dict[str, LocalExactSource] = {}

    async def readiness(self) -> ExecutionReadiness:
        return ExecutionReadiness(
            backend_id=self.backend_id,
            status=ReadinessStatus.READY,
            reason=(
                "local process execution is available through Work; exact Windows runs "
                "use KIS-owned Job Object containment"
            ),
        )

    async def prepare_exact_source(
        self,
        *,
        request_id: str,
        project: str,
        revision: str,
    ) -> LocalExactSource:
        source = await materialize_exact_source(
            self._runner,
            self._local,
            request_id=request_id,
            project=project,
            revision=revision,
        )
        self._prepared[request_id] = source
        return source

    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        if not self._profile_matches(request):
            return self._profile_mismatch(request)
        if request.source.exact:
            return await self._execute_exact(request)
        return await self._execute_mutable(request)

    def _profile_matches(self, request: ExecutionRequest) -> bool:
        return (
            request.profile.backend_id == self.backend_id
            and request.profile.profile_id == self._profile.profile_id
            and request.profile.image_id == self._profile.image_id
            and request.profile.toolchain_id == self._profile.toolchain_id
        )

    def _profile_mismatch(self, request: ExecutionRequest) -> ExecutionResult:
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
            lifecycle=(ExecutionLifecycleState.REQUESTED, ExecutionLifecycleState.INCOMPLETE),
        )

    async def _execute_mutable(self, request: ExecutionRequest) -> ExecutionResult:
        outcome = await run_nested_process(
            self._runner,
            command=_process_command(request),
            timeout_ms=request.timeout_ms,
        )
        evidence, truncated = clean_process_text(outcome.text, request.evidence_limit_chars)
        if outcome.exit_code is None:
            status, failure = "incomplete", "timeout_or_incomplete"
        elif outcome.exit_code == 0:
            status, failure = "passed", "none"
        else:
            status, failure = "failed", "execution_failed"
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

    async def _execute_exact(self, request: ExecutionRequest) -> ExecutionResult:
        source = self._prepared.get(request.request_id)
        if source is None:
            return self._source_failure(request, "source_identity_required", "exact source was not prepared")
        if (
            str(source.workspace) != request.source.project_path
            or source.revision != request.source.revision
        ):
            return self._source_failure(request, "source_mismatch", "prepared exact source identity changed")
        recheck = await run_nested_process(
            self._runner,
            command=_source_recheck_command(source),
            timeout_ms=min(self._local.materialize_timeout_ms, request.timeout_ms),
        )
        if (
            recheck.exit_code != 0
            or _marker(recheck.text, _SOURCE_REVISION_MARKER) != source.revision
            or _marker(recheck.text, _SOURCE_TREE_MARKER) != source.tree
        ):
            update_run_state(source, status="source_mismatch", authoritative=False)
            return self._source_failure(
                request,
                "source_mismatch",
                "exact workspace HEAD/tree/clean-state recheck failed",
            )
        update_run_state(source, status="starting", authoritative=False)
        try:
            await run_nested_process(
                self._runner,
                command=_worker_command(request, source),
                timeout_ms=(
                    request.timeout_ms
                    + self._local.worker_cleanup_grace_ms
                    + 5_000
                ),
            )
        except asyncio.CancelledError:
            (source.run_dir / "cancel.requested").touch(exist_ok=True)
            update_run_state(source, status="cancelling", authoritative=False)
            await _wait_for_worker_result(
                source.run_dir / WORKER_RESULT_NAME,
                self._local.worker_cleanup_grace_ms,
            )
            raise
        worker_result = _read_worker_result(source.run_dir / WORKER_RESULT_NAME)
        if worker_result is None:
            update_run_state(source, status="incomplete", authoritative=False)
            return self._source_failure(
                request,
                "lifecycle_failed",
                "containment worker did not produce a terminal result",
            )
        stdout_path = source.run_dir / "stdout.log"
        stderr_path = source.run_dir / "stderr.log"
        receipt_path, receipt_sha256, evidence_reference = write_exact_receipt(
            source,
            request,
            worker_result,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
        )
        stdout, stdout_truncated = _bounded_file_text(
            stdout_path, max(1, request.evidence_limit_chars // 2)
        )
        stderr, stderr_truncated = _bounded_file_text(
            stderr_path, max(1, request.evidence_limit_chars - len(stdout))
        )
        worker_status = str(worker_result.get("status", "unknown"))
        exit_code = worker_result.get("exit_code")
        if worker_status == "completed" and exit_code == 0:
            status, failure = "passed", "none"
        elif worker_status == "completed" and isinstance(exit_code, int):
            status, failure = "failed", "execution_failed"
        else:
            status, failure = "incomplete", "timeout_or_incomplete"
        authoritative = worker_status == "completed" and worker_result.get("job_assigned") is True
        update_run_state(
            source,
            status=status,
            authoritative=authoritative,
            receipt_path=str(receipt_path),
            receipt_sha256=receipt_sha256,
            evidence_reference=evidence_reference,
        )
        return ExecutionResult(
            request_id=request.request_id,
            backend_id=self.backend_id,
            status=status,
            exit_code=exit_code if isinstance(exit_code, int) else None,
            duration_ms=int(worker_result.get("duration_ms") or 0),
            source_revision=source.revision,
            image_id=self._profile.image_id,
            toolchain_id=self._profile.toolchain_id,
            cleanup=CleanupDisposition.NOT_REQUIRED,
            evidence=ExecutionEvidence(
                stdout=stdout,
                stderr=stderr,
                diagnostics=(
                    f"worker_status:{worker_status}",
                    f"worker_reason:{worker_result.get('reason', '')}",
                ),
                truncated=stdout_truncated or stderr_truncated,
                receipt_path=str(receipt_path),
                receipt_sha256=receipt_sha256,
                source_tree=source.tree,
                source_fingerprint=source.source_fingerprint,
                evidence_reference=evidence_reference,
            ),
            failure_classification=failure,
            lifecycle=(
                ExecutionLifecycleState.REQUESTED,
                ExecutionLifecycleState.MATERIALIZING,
                ExecutionLifecycleState.STARTING,
                ExecutionLifecycleState.EXECUTING,
                ExecutionLifecycleState.CAPTURING,
                ExecutionLifecycleState.COMPLETED
                if status != "incomplete"
                else ExecutionLifecycleState.INCOMPLETE,
            ),
        )

    def _source_failure(
        self,
        request: ExecutionRequest,
        failure: str,
        reason: str,
    ) -> ExecutionResult:
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
            evidence=ExecutionEvidence(diagnostics=(reason,)),
            failure_classification=failure,
            lifecycle=(
                ExecutionLifecycleState.REQUESTED,
                ExecutionLifecycleState.INCOMPLETE,
            ),
        )


def _process_command(request: ExecutionRequest) -> str:
    tokens = " ".join(_ps_quote(item) for item in (request.executable, *request.arguments))
    return (
        f"Set-Location -LiteralPath {_ps_quote(request.source.project_path)}; "
        f"& {tokens}; $kisCode = $LASTEXITCODE; "
        'Write-Output "__KIS_VERIFICATION_EXIT_CODE=$kisCode"; '
        "exit $kisCode"
    )


def _source_recheck_command(source: LocalExactSource) -> str:
    workspace = _ps_quote(str(source.workspace))
    revision = _ps_quote(source.revision)
    tree = _ps_quote(source.tree)
    return (
        "$ErrorActionPreference='Stop'; "
        f"$head = (& git -C {workspace} rev-parse HEAD).Trim(); "
        f"$actualTree = (& git -C {workspace} rev-parse ($head + '^{{tree}}')).Trim(); "
        f"$dirty = @(& git -C {workspace} status --porcelain --untracked-files=all); "
        f"if ($head -ne {revision} -or $actualTree -ne {tree} -or $dirty.Count -gt 0) {{ exit 94 }}; "
        'Write-Output ("__KIS_SOURCE_REVISION=" + $head); '
        'Write-Output ("__KIS_SOURCE_TREE=" + $actualTree); '
        'Write-Output "__KIS_VERIFICATION_EXIT_CODE=0"; exit 0'
    )


def _worker_command(request: ExecutionRequest, source: LocalExactSource) -> str:
    worker = Path(__file__).with_name("worker.py")
    values = (
        sys.executable,
        str(worker),
        "--state-dir", str(source.run_dir),
        "--cwd", str(source.workspace),
        "--timeout-ms", str(request.timeout_ms),
        "--parent-pid", str(os.getpid()),
        "--", request.executable, *request.arguments,
    )
    tokens = " ".join(_ps_quote(value) for value in values)
    return (
        f"& {tokens}; $kisCode = $LASTEXITCODE; "
        'Write-Output "__KIS_VERIFICATION_EXIT_CODE=$kisCode"; '
        "exit $kisCode"
    )


def _read_worker_result(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        return None
    return value


async def _wait_for_worker_result(path: Path, timeout_ms: int) -> None:
    deadline = asyncio.get_running_loop().time() + (timeout_ms / 1000)
    while asyncio.get_running_loop().time() < deadline:
        if path.is_file():
            return
        await asyncio.sleep(0.05)


def _bounded_file_text(path: Path, limit: int) -> tuple[str, bool]:
    try:
        value = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "", False
    return clean_process_text(value, limit)


def _marker(text: str, prefix: str) -> str | None:
    for line in reversed(text.splitlines()):
        value = line.strip()
        if value.startswith(prefix):
            return value[len(prefix):].strip().lower()
    return None


def _ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


__all__ = ["LocalProcessExecutionProvider", "LocalSourceError"]
