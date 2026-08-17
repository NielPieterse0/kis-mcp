from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from kis_mcp.execution.contracts import (
    ExecutionLifecycleState,
    ExecutionProfile,
    ExecutionRequest,
    ExecutionSource,
)
from kis_mcp.execution.hyperv import HyperVDisposableExecutionProvider
from kis_mcp.execution.settings import HyperVProfileSettings


class _Runner:
    def __init__(
        self,
        *,
        fail_fragment: str | None = None,
        fail_text: str = "phase failed",
    ) -> None:
        self.fail_fragment = fail_fragment
        self.fail_text = fail_text
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def __call__(self, tool: str, arguments: dict[str, Any]) -> Any:
        self.calls.append((tool, arguments))
        command = str(arguments.get("command", ""))
        if self.fail_fragment and self.fail_fragment in command:
            return {"text": f"{self.fail_text}\n__KIS_EXECUTION_EXIT_CODE=1\n"}
        if "Invoke-Command -VMName" in command:
            guest = json.dumps({"exit_code": 0, "stdout": "tests ok", "stderr": ""})
            return {"text": f"__KIS_GUEST_RESULT={guest}\n__KIS_EXECUTION_EXIT_CODE=0\n"}
        return {"text": "ok\n__KIS_EXECUTION_EXIT_CODE=0\n"}


def _config(tmp_path: Path) -> HyperVProfileSettings:
    return HyperVProfileSettings(
        template_vm="kis-windows-template",
        checkpoint_name="clean",
        state_root=str(tmp_path / "hyperv"),
        guest_workspace=r"C:\KIS\workspace",
        guest_username_env="KIS_HYPERV_GUEST_USERNAME",
        guest_password_env="KIS_HYPERV_GUEST_PASSWORD",
        startup_timeout_ms=60_000,
        cleanup_timeout_ms=30_000,
    )


def _provider(runner: _Runner, tmp_path: Path) -> HyperVDisposableExecutionProvider:
    return HyperVDisposableExecutionProvider(
        runner,
        _config(tmp_path),
        profile_id="windows-hyperv-proof",
        image_id="windows-hyperv-proof-v1",
        toolchain_id="repository-declared-v1",
    )


def _request() -> ExecutionRequest:
    return ExecutionRequest(
        request_id="proof-324",
        project_id="kis-mcp",
        verification_profile_id="python",
        source=ExecutionSource(
            project_path=r"C:\Projects\kis-mcp",
            revision="9adf1ca26a6a96a173605a7e5dd5c11216d6ec0e",
            exact=True,
        ),
        profile=ExecutionProfile(
            profile_id="windows-hyperv-proof",
            backend_id="windows-hyperv",
            image_id="windows-hyperv-proof-v1",
            toolchain_id="repository-declared-v1",
        ),
        executable="python",
        arguments=("-m", "pytest", "-q", "tests/test_contracts.py"),
        timeout_ms=120_000,
        evidence_limit_chars=20_000,
    )


def _commands(runner: _Runner) -> list[str]:
    return [str(arguments.get("command", "")) for _, arguments in runner.calls]


def test_hyperv_proof_orders_lifecycle_and_persists_host_evidence(tmp_path: Path) -> None:
    runner = _Runner()
    result = asyncio.run(
        _provider(runner, tmp_path).execute(_request())
    )

    commands = _commands(runner)
    fragments = [
        "Get-VMHost -ErrorAction",
        "git -C",
        "Export-VMSnapshot -VMSnapshot",
        "$guestAdapters | Disconnect-VMNetworkAdapter",
        "Start-VM -Name",
        "Copy-VMFile -Name",
        "Invoke-Command -VMName",
        "Set-VM -VM $vm",
        "$adapters | Disconnect-VMNetworkAdapter",
    ]
    assert [next(i for i, command in enumerate(commands) if fragment in command) for fragment in fragments] == sorted(
        next(i for i, command in enumerate(commands) if fragment in command) for fragment in fragments
    )
    assert result.status == "passed"
    assert result.cleanup.value == "quarantined"
    assert result.lifecycle == (
        ExecutionLifecycleState.REQUESTED,
        ExecutionLifecycleState.READINESS,
        ExecutionLifecycleState.MATERIALIZING,
        ExecutionLifecycleState.PROVISIONING,
        ExecutionLifecycleState.STARTING,
        ExecutionLifecycleState.TRANSFERRING,
        ExecutionLifecycleState.EXECUTING,
        ExecutionLifecycleState.CAPTURING,
        ExecutionLifecycleState.CLEANING,
        ExecutionLifecycleState.QUARANTINED,
        ExecutionLifecycleState.COMPLETED,
    )
    assert all("Remove-VM" not in command and "Remove-Item" not in command for command in commands)
    assert all("Connect-VMNetworkAdapter" not in command for command in commands)
    assert result.evidence.stdout == "tests ok"
    assert result.evidence.receipt_path is not None
    receipt = Path(result.evidence.receipt_path)
    assert receipt.exists()
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    assert payload["source_revision"] == _request().source.revision
    assert payload["lifecycle"][-1] == "completed"


def test_hyperv_cleanup_failure_quarantines_and_cannot_return_passed(tmp_path: Path) -> None:
    runner = _Runner(fail_fragment="Set-VM -VM")
    result = asyncio.run(
        _provider(runner, tmp_path).execute(_request())
    )

    assert result.status == "incomplete"
    assert result.cleanup.value == "quarantined"
    assert result.failure_classification == "cleanup_failed"
    assert result.lifecycle[-2:] == (
        ExecutionLifecycleState.QUARANTINED,
        ExecutionLifecycleState.INCOMPLETE,
    )
    assert any("KIS_QUARANTINED" in command for command in _commands(runner))


def test_hyperv_repeated_request_allocates_fresh_attempt_state(tmp_path: Path) -> None:
    runner = _Runner()
    provider = _provider(runner, tmp_path)

    first = asyncio.run(provider.execute(_request()))
    second = asyncio.run(provider.execute(_request()))

    assert first.status == second.status == "passed"
    assert first.evidence.receipt_path != second.evidence.receipt_path
    namespaces = list((tmp_path / "hyperv" / "requests").iterdir())
    assert len(namespaces) == 1
    assert [item.name for item in sorted(namespaces[0].iterdir())] == ["000001", "000002"]
    starts = [command for command in _commands(runner) if "Start-VM -Name" in command]
    assert len(starts) == 2
    assert starts[0] != starts[1]


def test_hyperv_missing_prerequisites_fail_before_guest_creation(tmp_path: Path) -> None:
    runner = _Runner(fail_fragment="Get-VMHost")
    result = asyncio.run(
        _provider(runner, tmp_path).execute(_request())
    )

    assert result.status == "incomplete"
    assert result.failure_classification == "backend_unavailable"
    assert not any("Export-VMSnapshot -VMSnapshot" in command for command in _commands(runner))


def test_hyperv_requires_exact_source_identity(tmp_path: Path) -> None:
    request = _request()
    inexact = ExecutionRequest(
        request_id=request.request_id,
        project_id=request.project_id,
        verification_profile_id=request.verification_profile_id,
        source=ExecutionSource(
            project_path=request.source.project_path,
            revision="working-tree",
            exact=False,
        ),
        profile=request.profile,
        executable=request.executable,
        arguments=request.arguments,
        timeout_ms=request.timeout_ms,
        evidence_limit_chars=request.evidence_limit_chars,
    )
    runner = _Runner()
    result = asyncio.run(_provider(runner, tmp_path).execute(inexact))

    assert result.status == "incomplete"
    assert result.failure_classification == "source_identity_required"
    assert runner.calls == []


def test_hyperv_rejects_profile_identity_mismatch_before_host_work(tmp_path: Path) -> None:
    request = _request()
    mismatched = ExecutionRequest(
        request_id=request.request_id,
        project_id=request.project_id,
        verification_profile_id=request.verification_profile_id,
        source=request.source,
        profile=ExecutionProfile(
            profile_id=request.profile.profile_id,
            backend_id=request.profile.backend_id,
            image_id="stale-image-v0",
            toolchain_id=request.profile.toolchain_id,
        ),
        executable=request.executable,
        arguments=request.arguments,
        timeout_ms=request.timeout_ms,
        evidence_limit_chars=request.evidence_limit_chars,
    )
    runner = _Runner()
    result = asyncio.run(_provider(runner, tmp_path).execute(mismatched))

    assert result.status == "incomplete"
    assert result.failure_classification == "profile_identity_mismatch"
    assert runner.calls == []


def test_hyperv_source_mismatch_stops_before_guest_provisioning(tmp_path: Path) -> None:
    runner = _Runner(
        fail_fragment="git -C",
        fail_text=(
            "KIS_SOURCE_MISMATCH expected=9adf1ca26a6a96a173605a7e5dd5c11216d6ec0e "
            "actual=1111111111111111111111111111111111111111"
        ),
    )
    result = asyncio.run(_provider(runner, tmp_path).execute(_request()))

    assert result.status == "incomplete"
    assert result.failure_classification == "source_mismatch"
    assert not any(
        "Export-VMSnapshot -VMSnapshot" in command for command in _commands(runner)
    )
    assert result.lifecycle[-1] == ExecutionLifecycleState.INCOMPLETE
