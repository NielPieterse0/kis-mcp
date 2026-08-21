from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

import kis_mcp.commissioning_runtime.runner as runner_module
from kis_mcp.commissioning.models import (
    ChangeClassification,
    ClassificationState,
    CommissioningObligation,
    LandedChangeEvidence,
)
from kis_mcp.commissioning.runner import FrozenCommissioningExecution
from kis_mcp.commissioning.settings import load_post_merge_commissioning_settings
from kis_mcp.commissioning_runtime.probes import RuntimeGenerationGate
from kis_mcp.commissioning_runtime.runner import CommissioningRunnerService
from kis_mcp.commissioning_runtime.state import (
    CommissioningStateStore,
    ExecutionResult,
)

MERGE = "a" * 40
KEY = f"commission:nielpieterse0/kis-mcp:{MERGE}:work-management"


def _frozen(*, refresh_rule: str = "none", probe_id: str = "work-management-contract") -> FrozenCommissioningExecution:
    return FrozenCommissioningExecution(
        repository="NielPieterse0/kis-mcp",
        commissioning_issue=460,
        source_issue=454,
        source_pr=456,
        merge_sha=MERGE,
        change_id="229-commissioning-runner-evidence-lifecycle",
        surface_id="work-management",
        commissioning_key=KEY,
        runtime_instance="kis-op",
        refresh_rule=refresh_rule,
        probe_id=probe_id,
        verification_procedure="procedure",
        expected_invariant="invariant",
        evidence_target="target",
        terminal_success_criterion="criterion",
    )

def _evidence() -> LandedChangeEvidence:
    return LandedChangeEvidence(
        repository="NielPieterse0/kis-mcp",
        source_issue=454,
        source_pr=456,
        merge_sha=MERGE,
        change_id="229-commissioning-runner-evidence-lifecycle",
        changed_paths=("src/kis_mcp/work_management/service.py",),
        risk_triggers=("public_contract",),
    )


def _classification(frozen: FrozenCommissioningExecution) -> ChangeClassification:
    obligation = CommissioningObligation(
        surface_id=frozen.surface_id,
        commissioning_key=frozen.commissioning_key,
        runtime_instance=frozen.runtime_instance,
        refresh_rule=frozen.refresh_rule,
        probe_id=frozen.probe_id,
        verification_procedure=frozen.verification_procedure,
        expected_invariant=frozen.expected_invariant,
        evidence_target=frozen.evidence_target,
        terminal_success_criterion=frozen.terminal_success_criterion,
        matched_paths=("src/kis_mcp/work_management/service.py",),
        matched_risk_triggers=(),
    )
    return ChangeClassification(
        state=ClassificationState.REQUIRED,
        obligations=(obligation,),
    )


async def _identity(_repository: str, _issue: int, _invoker: Any) -> tuple:
    frozen = _frozen()
    return frozen, _evidence(), _classification(frozen)


class FakeInvoker:
    def __init__(self, *, probe_passes: bool = True) -> None:
        self.probe_passes = probe_passes
        self.work_state = "active"
        self.source_state = "open"
        self.read_calls: list[tuple[str, dict[str, Any]]] = []
        self.change_calls: list[tuple[str, dict[str, Any]]] = []
        self.external_calls: list[tuple[str, dict[str, Any]]] = []

    async def read(self, operation: str, arguments: dict[str, Any]) -> Any:
        self.read_calls.append((operation, dict(arguments)))
        if operation == "project_management_board_data":
            number = int(arguments["query"])
            return {
                "provenance": {"complete": True},
                "result": {
                    "complete": True,
                    "truncated": False,
                    "cards": [
                        {
                            "item_id": f"ITEM-{number}",
                            "repository": "NielPieterse0/kis-mcp",
                            "number": number,
                            "title": f"issue {number}",
                            "source_state": self.source_state if number == 460 else "closed",
                            "work_state": self.work_state if number == 460 else "done",
                            "execution_owner": "codex" if number == 460 else None,
                            "priority": "high",
                            "effort": "medium",
                            "record_type": "task",
                            "authority_revision": f"rev-{number}",
                        }
                    ],
                },
            }
        if operation == "project_management_contract":
            domains = [
                {"id": "source_verification", "field": "Verification"},
                {"id": "live_verification", "field": "Live Verification"},
            ] if self.probe_passes else []
            return {
                "schema_version": 1,
                "canonical_contracts": {"work_lifecycle_operations": {"verification_domains": domains}},
            }
        raise AssertionError(operation)

    async def change(self, operation: str, arguments: dict[str, Any]) -> Any:
        self.change_calls.append((operation, dict(arguments)))
        if operation == "project_management_reconcile":
            return {"outcomes": [{"success": True, "applied": True}]}
        if operation == "project_management_complete_work":
            self.work_state = "done"
            return {
                "mode": "apply",
                "outcomes": [{"success": True, "applied": True}],
                "source_close_required": True,
            }
        if operation == "project_management_transition_work":
            self.work_state = str(arguments["target"])
            return {"outcomes": [{"success": True, "applied": True}]}
        raise AssertionError(operation)

    async def external(self, operation: str, arguments: dict[str, Any]) -> Any:
        self.external_calls.append((operation, dict(arguments)))
        if operation == "github_issue_write":
            self.source_state = "closed"
            return {"number": arguments["issue_number"], "state": "closed"}
        raise AssertionError(operation)


def _service(
    tmp_path: Path,
    invoker: FakeInvoker,
    *,
    identity_resolver: Any = _identity,
) -> CommissioningRunnerService:
    return CommissioningRunnerService(
        load_post_merge_commissioning_settings(),
        CommissioningStateStore(tmp_path, retention=20),
        invoker=invoker,
        identity_resolver=identity_resolver,
    )


def test_passed_runner_projects_source_completes_work_and_closes_issue(tmp_path: Path) -> None:
    invoker = FakeInvoker()
    result = asyncio.run(
        _service(tmp_path, invoker).run(
            "NielPieterse0/kis-mcp", 460, execution_owner="codex"
        )
    )
    assert result["result"] == "passed"
    assert result["replayed"] is False
    operations = [name for name, _args in invoker.change_calls]
    assert "project_management_reconcile" in operations
    assert "project_management_complete_work" in operations
    projection = next(
        args for name, args in invoker.change_calls
        if name == "project_management_reconcile" and "Live Verification" in args["supported_fields"]
    )
    assert "Verification" not in projection["supported_fields"]
    assert projection["desired"][0]["fields"]["Live Verification"] == "Passed"
    assert invoker.external_calls[-1][0] == "github_issue_write"
    assert invoker.external_calls[-1][1]["state"] == "closed"


def test_failed_probe_stays_visible_and_does_not_close_issue(tmp_path: Path) -> None:
    invoker = FakeInvoker(probe_passes=False)
    result = asyncio.run(
        _service(tmp_path, invoker).run(
            "NielPieterse0/kis-mcp", 460, execution_owner="codex"
        )
    )
    assert result["result"] == "failed"
    assert all(name != "project_management_complete_work" for name, _ in invoker.change_calls)
    assert invoker.external_calls == []
    projection = next(args for name, args in invoker.change_calls if name == "project_management_reconcile")
    assert projection["desired"][0]["fields"]["Live Verification"] == "Failed"


def test_passed_replay_does_not_repeat_mutations(tmp_path: Path) -> None:
    invoker = FakeInvoker()
    service = _service(tmp_path, invoker)
    first = asyncio.run(
        service.run("NielPieterse0/kis-mcp", 460, execution_owner="codex")
    )
    mutation_count = len(invoker.change_calls) + len(invoker.external_calls)
    read_count = len(invoker.read_calls)
    assert invoker.work_state == "done"
    assert invoker.source_state == "closed"
    second = asyncio.run(
        service.run("NielPieterse0/kis-mcp", 460, execution_owner="codex")
    )
    assert first["result"] == second["result"] == "passed"
    assert second["replayed"] is True
    assert len(invoker.change_calls) + len(invoker.external_calls) == mutation_count
    assert len(invoker.read_calls) == read_count


async def _identity_restart(_repository: str, _issue: int, _invoker: Any) -> tuple:
    frozen = _frozen(refresh_rule="restart")
    return frozen, _evidence(), _classification(frozen)


def test_blocked_runtime_refresh_stays_open_then_explicit_retry_passes(
    tmp_path: Path, monkeypatch: Any
) -> None:
    gates = [
        RuntimeGenerationGate(False, "runtime_refresh_required", "b" * 40),
        RuntimeGenerationGate(True, "runtime_generation_current", "c" * 40),
    ]

    async def fake_gate(*_args: Any, **_kwargs: Any) -> RuntimeGenerationGate:
        return gates.pop(0)

    monkeypatch.setattr(runner_module, "runtime_generation_gate", fake_gate)
    invoker = FakeInvoker()
    service = _service(tmp_path, invoker, identity_resolver=_identity_restart)
    first = asyncio.run(
        service.run("NielPieterse0/kis-mcp", 460, execution_owner="codex")
    )
    assert first["result"] == "blocked"
    assert any(name == "project_management_transition_work" for name, _ in invoker.change_calls)
    assert invoker.external_calls == []

    invoker.work_state = "active"
    invoker.source_state = "open"
    second = asyncio.run(
        service.run(
            "NielPieterse0/kis-mcp", 460, execution_owner="codex", retry=True
        )
    )
    assert second["result"] == "passed"
    assert second["attempt"] == 2
    assert invoker.external_calls[-1][0] == "github_issue_write"

def test_failed_probe_requires_explicit_retry_before_later_pass(tmp_path: Path) -> None:
    invoker = FakeInvoker(probe_passes=False)
    service = _service(tmp_path, invoker)
    first = asyncio.run(
        service.run("NielPieterse0/kis-mcp", 460, execution_owner="codex")
    )
    mutation_count = len(invoker.change_calls) + len(invoker.external_calls)
    replay = asyncio.run(
        service.run("NielPieterse0/kis-mcp", 460, execution_owner="codex")
    )
    assert first["result"] == replay["result"] == "failed"
    assert replay["replayed"] is True
    assert len(invoker.change_calls) + len(invoker.external_calls) == mutation_count

    invoker.probe_passes = True
    retried = asyncio.run(
        service.run(
            "NielPieterse0/kis-mcp", 460, execution_owner="codex", retry=True
        )
    )
    assert retried["result"] == "passed"
    assert retried["attempt"] == 2
    assert invoker.external_calls[-1][0] == "github_issue_write"

def test_interrupted_proof_persisted_resume_does_not_repeat_live_probe(tmp_path: Path) -> None:
    invoker = FakeInvoker()
    service = _service(tmp_path, invoker)
    frozen = _frozen()
    now = datetime(2026, 8, 21, 20, 0, tzinfo=UTC)
    state = service.store.begin_execution(
        KEY,
        runner_module._fingerprint(frozen),
        now,
    )
    receipt = service.store.persist_receipt(
        {"schema_version": 1, "kind": "execution", "result": "passed"},
        now,
    )
    service.store.update_execution(
        state,
        phase="proof_persisted",
        result=ExecutionResult.PASSED,
        receipt_id=receipt.receipt_id,
        updated_at=now,
    )

    result = asyncio.run(
        service.run("NielPieterse0/kis-mcp", 460, execution_owner="codex")
    )
    assert result["result"] == "passed"
    assert all(name != "project_management_contract" for name, _ in invoker.read_calls)
    assert invoker.external_calls[-1][0] == "github_issue_write"

def test_initial_execution_requires_open_claimed_commissioning_issue(
    tmp_path: Path,
) -> None:
    invoker = FakeInvoker()
    invoker.source_state = "closed"
    service = _service(tmp_path, invoker)

    with pytest.raises(RuntimeError, match="open, uniquely Active"):
        asyncio.run(
            service.run(
                "NielPieterse0/kis-mcp",
                460,
                execution_owner="codex",
            )
        )
    assert invoker.change_calls == []
    assert invoker.external_calls == []
    assert service.store.load_execution_state(KEY) is None

def test_resume_after_work_completion_skips_duplicate_complete_work(
    tmp_path: Path,
) -> None:
    invoker = FakeInvoker()
    service = _service(tmp_path, invoker)
    frozen = _frozen()
    now = datetime(2026, 8, 21, 20, 0, tzinfo=UTC)
    state = service.store.begin_execution(
        KEY, runner_module._fingerprint(frozen), now
    )
    receipt = service.store.persist_receipt(
        {"schema_version": 1, "kind": "execution", "result": "passed"}, now
    )
    service.store.update_execution(
        state,
        phase="source_projected",
        result=ExecutionResult.PASSED,
        receipt_id=receipt.receipt_id,
        updated_at=now,
    )
    invoker.work_state = "done"

    result = asyncio.run(
        service.run("NielPieterse0/kis-mcp", 460, execution_owner="codex")
    )
    assert result["result"] == "passed"
    assert all(name != "project_management_complete_work" for name, _ in invoker.change_calls)
    assert invoker.external_calls[-1][0] == "github_issue_write"

def test_resume_after_block_transition_skips_duplicate_transition(
    tmp_path: Path,
) -> None:
    invoker = FakeInvoker()
    service = _service(tmp_path, invoker)
    frozen = _frozen()
    now = datetime(2026, 8, 21, 20, 0, tzinfo=UTC)
    state = service.store.begin_execution(
        KEY, runner_module._fingerprint(frozen), now
    )
    receipt = service.store.persist_receipt(
        {"schema_version": 1, "kind": "execution", "result": "blocked"}, now
    )
    service.store.update_execution(
        state,
        phase="source_projected",
        result=ExecutionResult.BLOCKED,
        receipt_id=receipt.receipt_id,
        updated_at=now,
    )
    invoker.work_state = "blocked"

    result = asyncio.run(
        service.run("NielPieterse0/kis-mcp", 460, execution_owner="codex")
    )
    assert result["result"] == "blocked"
    assert all(
        name != "project_management_transition_work" for name, _ in invoker.change_calls
    )

def test_aggregate_projection_is_content_addressed_across_resume(
    tmp_path: Path,
) -> None:
    invoker = FakeInvoker()
    service = _service(tmp_path, invoker)
    frozen = _frozen()
    now = datetime(2026, 8, 21, 20, 0, tzinfo=UTC)
    state = service.store.begin_execution(
        KEY, runner_module._fingerprint(frozen), now
    )
    receipt = service.store.persist_receipt(
        {"schema_version": 1, "kind": "execution", "result": "passed"}, now
    )
    service.store.update_execution(
        state,
        phase="proof_persisted",
        result=ExecutionResult.PASSED,
        receipt_id=receipt.receipt_id,
        updated_at=now,
    )
    target = service.settings.targets[0]
    first = asyncio.run(
        service._project_aggregate(target, _evidence(), _classification(frozen))
    )
    second = asyncio.run(
        service._project_aggregate(target, _evidence(), _classification(frozen))
    )
    assert first == second
    reconciles = [args for name, args in invoker.change_calls if name == "project_management_reconcile"]
    assert reconciles[-2]["idempotency_key"] == reconciles[-1]["idempotency_key"]

def test_retry_claim_rejection_does_not_create_next_attempt(tmp_path: Path) -> None:
    invoker = FakeInvoker(probe_passes=False)
    service = _service(tmp_path, invoker)
    first = asyncio.run(
        service.run("NielPieterse0/kis-mcp", 460, execution_owner="codex")
    )
    assert first["result"] == "failed"
    invoker.work_state = "blocked"

    with pytest.raises(RuntimeError, match="Active"):
        asyncio.run(
            service.run(
                "NielPieterse0/kis-mcp",
                460,
                execution_owner="codex",
                retry=True,
            )
        )
    state = service.store.load_execution_state(KEY)
    assert state is not None
    assert state.attempt == 1
    assert state.result is ExecutionResult.FAILED