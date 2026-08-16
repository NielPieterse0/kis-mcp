from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Mapping

from kis_mcp.housekeeping.contracts import (
    FindingKind,
    HousekeepingTrigger,
    RunMode,
    RunnerKind,
)
from kis_mcp.housekeeping.work_management import (
    HousekeepingRunConfig,
    run_backlog_readiness,
    run_work_management_reconciliation,
)


class FakeInvoker:
    def __init__(self, *, inventory: dict[str, Any]) -> None:
        self.inventory = inventory
        self.selection: dict[str, Any] = {"selected": None, "evaluations": []}
        self.change_calls: list[tuple[str, dict[str, Any]]] = []
        self.source_states: dict[tuple[str, int], str] = {}

    async def read(self, operation: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
        if operation == "project_management_inventory":
            return self.inventory
        if operation == "project_management_next_work":
            return self.selection
        raise AssertionError(operation)

    async def change(self, operation: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
        self.change_calls.append((operation, dict(arguments)))
        return {"outcomes": [{"action": "create", "success": True}]}

    async def external(self, operation: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
        assert operation == "github_issue_read"
        owner = str(arguments["owner"])
        repo = str(arguments["repo"])
        number = int(arguments["issue_number"])
        return {"state": self.source_states.get((f"{owner}/{repo}".casefold(), number), "open")}


def _config(root: Path) -> HousekeepingRunConfig:
    return HousekeepingRunConfig(
        project_id="kis-mcp",
        repository="NielPieterse0/kis-mcp",
        repository_root=root,
    )


def _scope(root: Path, change_id: str, number: int) -> None:
    path = root / ".work" / "changes" / change_id
    path.mkdir(parents=True)
    (path / "scope.json").write_text(
        json.dumps(
            {
                "change_id": change_id,
                "status": "active",
                "work_management": {
                    "source_repository": "NielPieterse0/kis-mcp",
                    "source_number": number,
                    "source_kind": "issue",
                },
            }
        ),
        encoding="utf-8",
    )


def test_reconciliation_plans_exact_missing_project_capture(tmp_path: Path) -> None:
    _scope(tmp_path, "176-example", 325)
    invoker = FakeInvoker(inventory={"items": [], "truncated": False})
    trigger = HousekeepingTrigger(runner=RunnerKind.WORK_MANAGEMENT_RECONCILIATION)

    receipt = asyncio.run(run_work_management_reconciliation(invoker, _config(tmp_path), trigger))

    assert [finding.kind for finding in receipt.findings] == [FindingKind.MISSING_PROJECT_RECORD]
    assert len(receipt.actions) == 1
    action = receipt.actions[0]
    assert action.operation == "project_management_reconcile"
    desired = action.arguments["desired"][0]
    assert desired["source_number"] == 325
    assert desired["fields"] == {}
    assert receipt.metrics.safe_actions == 1


def test_reconciliation_apply_uses_bounded_idempotency(tmp_path: Path) -> None:
    _scope(tmp_path, "176-example", 325)
    invoker = FakeInvoker(inventory={"items": [], "truncated": False})
    trigger = HousekeepingTrigger(
        runner=RunnerKind.WORK_MANAGEMENT_RECONCILIATION,
        mode=RunMode.APPLY,
        idempotency_key="run-1",
    )

    receipt = asyncio.run(run_work_management_reconciliation(invoker, _config(tmp_path), trigger))

    assert receipt.metrics.applied_actions == 1
    applied = invoker.change_calls[-1][1]
    assert applied["apply"] is True
    assert applied["idempotency_key"] == "run-1:capture:nielpieterse0/kis-mcp#325"


def test_reconciliation_fails_closed_on_truncated_inventory(tmp_path: Path) -> None:
    invoker = FakeInvoker(inventory={"items": [], "truncated": True})
    trigger = HousekeepingTrigger(runner=RunnerKind.WORK_MANAGEMENT_RECONCILIATION)

    receipt = asyncio.run(run_work_management_reconciliation(invoker, _config(tmp_path), trigger))

    assert receipt.complete is False
    assert receipt.conflicts == ("inventory_truncated",)
    assert receipt.findings[0].kind is FindingKind.INVENTORY_INCOMPLETE
    assert not receipt.actions


def test_reconciliation_reports_closed_source_active_claim_without_mutating(tmp_path: Path) -> None:
    item = {
        "kind": "issue",
        "repository": "NielPieterse0/kis-mcp",
        "number": 42,
        "state": "closed",
        "field_values": [
            {"field_name": "Status", "value": "Active"},
            {"field_name": "Execution Owner", "value": "agentX"},
            {"field_name": "Change ID", "value": "missing-change"},
        ],
    }
    invoker = FakeInvoker(inventory={"items": [item], "truncated": False})
    trigger = HousekeepingTrigger(runner=RunnerKind.WORK_MANAGEMENT_RECONCILIATION)

    receipt = asyncio.run(run_work_management_reconciliation(invoker, _config(tmp_path), trigger))

    kinds = {finding.kind for finding in receipt.findings}
    assert FindingKind.SOURCE_CLOSED_PROJECT_ACTIVE in kinds
    assert FindingKind.STALE_EXECUTION_CLAIM in kinds
    assert FindingKind.CHANGE_PROJECTION_MISSING in kinds
    assert not receipt.actions


def _blocked_item(number: int, blocked_by: str | None = None) -> dict[str, Any]:
    values = [
        {"field_name": "Status", "value": "Blocked"},
        {"field_name": "Record Type", "value": "Task"},
        {"field_name": "Priority", "value": "High"},
        {"field_name": "Effort", "value": "Small"},
        {"field_name": "Documentation Impact", "value": "None"},
        {"field_name": "Execution Owner", "value": None},
        {"field_name": "Blocked By", "value": blocked_by},
    ]
    return {
        "kind": "issue",
        "repository": "NielPieterse0/kis-mcp",
        "number": number,
        "state": "open",
        "field_values": values,
    }


def test_backlog_readiness_promotes_mechanically_unblocked_work(tmp_path: Path) -> None:
    invoker = FakeInvoker(inventory={"items": [_blocked_item(51)], "truncated": False})
    invoker.selection = {"selected": {"number": 99}, "evaluations": []}
    trigger = HousekeepingTrigger(runner=RunnerKind.BACKLOG_READINESS)

    receipt = asyncio.run(run_backlog_readiness(invoker, _config(tmp_path), trigger))

    assert receipt.selection == invoker.selection
    assert FindingKind.BLOCKED_WITHOUT_DEPENDENCY in {item.kind for item in receipt.findings}
    assert len(receipt.actions) == 1
    action = receipt.actions[0]
    assert action.operation == "project_management_transition_work"
    assert action.arguments["target"] == "ready"
    assert action.arguments["issue_number"] == 51


def test_backlog_readiness_reports_resolved_exact_dependency(tmp_path: Path) -> None:
    invoker = FakeInvoker(inventory={"items": [_blocked_item(52, "#10")], "truncated": False})
    invoker.source_states[("nielpieterse0/kis-mcp", 10)] = "closed"
    trigger = HousekeepingTrigger(runner=RunnerKind.BACKLOG_READINESS)

    receipt = asyncio.run(run_backlog_readiness(invoker, _config(tmp_path), trigger))

    kinds = {item.kind for item in receipt.findings}
    assert FindingKind.RESOLVED_DEPENDENCY_STILL_BLOCKING in kinds
    assert not receipt.actions


def test_backlog_readiness_reports_ambiguous_dependency_text(tmp_path: Path) -> None:
    invoker = FakeInvoker(
        inventory={"items": [_blocked_item(53, "waiting for upstream approval")], "truncated": False}
    )
    trigger = HousekeepingTrigger(runner=RunnerKind.BACKLOG_READINESS)

    receipt = asyncio.run(run_backlog_readiness(invoker, _config(tmp_path), trigger))

    kinds = {item.kind for item in receipt.findings}
    assert FindingKind.AMBIGUOUS_DEPENDENCY in kinds
    assert not receipt.actions


def test_reconciliation_reports_missing_change_projection_for_bound_item(tmp_path: Path) -> None:
    _scope(tmp_path, "176-bound", 61)
    item = {
        "kind": "issue",
        "repository": "NielPieterse0/kis-mcp",
        "number": 61,
        "state": "open",
        "field_values": [
            {"field_name": "Status", "value": "Active"},
            {"field_name": "Record Type", "value": "Task"},
            {"field_name": "Priority", "value": "High"},
            {"field_name": "Effort", "value": "Small"},
            {"field_name": "Documentation Impact", "value": "None"},
            {"field_name": "Change ID", "value": None},
        ],
    }
    invoker = FakeInvoker(inventory={"items": [item], "truncated": False})
    trigger = HousekeepingTrigger(runner=RunnerKind.WORK_MANAGEMENT_RECONCILIATION)

    receipt = asyncio.run(run_work_management_reconciliation(invoker, _config(tmp_path), trigger))

    findings = [item for item in receipt.findings if item.kind is FindingKind.CHANGE_PROJECTION_MISSING]
    assert len(findings) == 1
    assert findings[0].evidence["expected_change_id"] == "176-bound"
    assert findings[0].evidence["observed_change_id"] is None


class FailingInventoryInvoker(FakeInvoker):
    async def read(self, operation: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
        if operation == "project_management_inventory":
            raise RuntimeError("provider unavailable")
        return await super().read(operation, arguments)


def test_reconciliation_returns_typed_receipt_when_authority_is_unavailable(tmp_path: Path) -> None:
    invoker = FailingInventoryInvoker(inventory={"items": [], "truncated": False})
    trigger = HousekeepingTrigger(runner=RunnerKind.WORK_MANAGEMENT_RECONCILIATION)

    receipt = asyncio.run(run_work_management_reconciliation(invoker, _config(tmp_path), trigger))

    assert receipt.complete is False
    assert receipt.conflicts == ("authority_unavailable",)
    assert receipt.findings[0].kind is FindingKind.AUTHORITY_UNAVAILABLE
    assert receipt.metrics.source_failures == 1


def test_backlog_returns_typed_receipt_when_authority_is_unavailable(tmp_path: Path) -> None:
    invoker = FailingInventoryInvoker(inventory={"items": [], "truncated": False})
    trigger = HousekeepingTrigger(runner=RunnerKind.BACKLOG_READINESS)

    receipt = asyncio.run(run_backlog_readiness(invoker, _config(tmp_path), trigger))

    assert receipt.complete is False
    assert receipt.findings[0].kind is FindingKind.AUTHORITY_UNAVAILABLE


def test_reconciliation_marks_source_scan_incomplete_and_does_not_apply(tmp_path: Path) -> None:
    _scope(tmp_path, "176-first", 71)
    _scope(tmp_path, "176-second", 72)
    invoker = FakeInvoker(inventory={"items": [], "truncated": False})
    config = HousekeepingRunConfig(
        project_id="kis-mcp",
        repository="NielPieterse0/kis-mcp",
        repository_root=tmp_path,
        max_external_reads=1,
    )
    trigger = HousekeepingTrigger(
        runner=RunnerKind.WORK_MANAGEMENT_RECONCILIATION,
        mode=RunMode.APPLY,
        idempotency_key="bounded-run",
    )

    receipt = asyncio.run(run_work_management_reconciliation(invoker, config, trigger))

    assert receipt.complete is False
    assert "source_evidence_incomplete" in receipt.conflicts
    assert FindingKind.SOURCE_EVIDENCE_INCOMPLETE in {item.kind for item in receipt.findings}
    assert receipt.applied_receipts == ()
