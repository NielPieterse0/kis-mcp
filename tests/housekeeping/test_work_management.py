from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Mapping

from kis_mcp.housekeeping import (
    FindingKind,
    HousekeepingRunConfig,
    HousekeepingTrigger,
    RunMode,
    RunnerKind,
    run_backlog_readiness,
    run_work_management_reconciliation,
)


class FakeInvoker:
    def __init__(self, *, inventory: dict[str, Any]) -> None:
        self.inventory = inventory
        self.selection: dict[str, Any] = {
            "selected": None,
            "evaluations": [],
            "complete": True,
        }
        self.change_calls: list[tuple[str, dict[str, Any]]] = []
        self.source_states: dict[tuple[str, int], str] = {}
        self.fail_sources: set[tuple[str, int]] = set()
        self.external_calls: list[tuple[str, int]] = []
        self.fail_change_operation: str | None = None
        self.reject_ready_preview = False

    async def read(
        self, operation: str, arguments: Mapping[str, Any]
    ) -> dict[str, Any]:
        if operation == "project_management_inventory":
            return self.inventory
        if operation == "project_management_next_work":
            return self.selection
        raise AssertionError(operation)

    async def change(
        self, operation: str, arguments: Mapping[str, Any]
    ) -> dict[str, Any]:
        self.change_calls.append((operation, dict(arguments)))
        if operation == self.fail_change_operation and arguments.get("apply") is True:
            raise RuntimeError("apply failed")
        if (
            operation == "project_management_transition_work"
            and arguments.get("apply") is False
            and self.reject_ready_preview
        ):
            return {"outcomes": [{"action": "update", "success": False}]}
        action = "create" if operation == "project_management_reconcile" else "update"
        return {"outcomes": [{"action": action, "success": True}]}

    async def external(
        self, operation: str, arguments: Mapping[str, Any]
    ) -> dict[str, Any]:
        assert operation == "github_issue_read"
        repository = f"{arguments['owner']}/{arguments['repo']}".casefold()
        number = int(arguments["issue_number"])
        self.external_calls.append((repository, number))
        if (repository, number) in self.fail_sources:
            raise RuntimeError("source unavailable")
        return {"state": self.source_states.get((repository, number), "open")}


def _config(root: Path, *, max_external_reads: int = 100) -> HousekeepingRunConfig:
    return HousekeepingRunConfig(
        project_id="kis-mcp",
        repository="NielPieterse0/kis-mcp",
        repository_root=root,
        max_external_reads=max_external_reads,
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


def _item(
    number: int,
    *,
    status: str = "Blocked",
    state: str = "open",
    blocked_by: str | None = None,
    owner: str | None = None,
    change_id: str | None = None,
) -> dict[str, Any]:
    return {
        "kind": "issue",
        "repository": "NielPieterse0/kis-mcp",
        "number": number,
        "state": state,
        "field_values": [
            {"field_name": "Status", "value": status},
            {"field_name": "Record Type", "value": "Task"},
            {"field_name": "Priority", "value": "High"},
            {"field_name": "Effort", "value": "Small"},
            {"field_name": "Documentation Impact", "value": "None"},
            {"field_name": "Execution Owner", "value": owner},
            {"field_name": "Change ID", "value": change_id},
            {"field_name": "Blocked By", "value": blocked_by},
        ],
    }


def test_reconciliation_plans_exact_missing_project_capture(tmp_path: Path) -> None:
    _scope(tmp_path, "194-example", 364)
    invoker = FakeInvoker(inventory={"items": [], "truncated": False})
    trigger = HousekeepingTrigger(runner=RunnerKind.WORK_MANAGEMENT_RECONCILIATION)

    receipt = asyncio.run(
        run_work_management_reconciliation(invoker, _config(tmp_path), trigger)
    )

    assert [finding.kind for finding in receipt.findings] == [
        FindingKind.MISSING_PROJECT_RECORD
    ]
    assert len(receipt.actions) == 1
    action = receipt.actions[0]
    assert action.operation == "project_management_reconcile"
    assert action.arguments["desired"][0]["source_number"] == 364
    assert receipt.metrics.safe_actions == 1


def test_reconciliation_apply_derives_action_idempotency_key(tmp_path: Path) -> None:
    _scope(tmp_path, "194-example", 364)
    invoker = FakeInvoker(inventory={"items": [], "truncated": False})
    trigger = HousekeepingTrigger(
        runner=RunnerKind.WORK_MANAGEMENT_RECONCILIATION,
        mode=RunMode.APPLY,
        idempotency_key="run-194",
    )

    receipt = asyncio.run(
        run_work_management_reconciliation(invoker, _config(tmp_path), trigger)
    )

    assert receipt.metrics.applied_actions == 1
    applied = invoker.change_calls[-1][1]
    assert applied["apply"] is True
    assert applied["idempotency_key"] == (
        "run-194:capture:nielpieterse0/kis-mcp#364"
    )


def test_reconciliation_fails_closed_on_truncated_inventory(tmp_path: Path) -> None:
    invoker = FakeInvoker(inventory={"items": [], "truncated": True})
    trigger = HousekeepingTrigger(runner=RunnerKind.WORK_MANAGEMENT_RECONCILIATION)

    receipt = asyncio.run(
        run_work_management_reconciliation(invoker, _config(tmp_path), trigger)
    )

    assert receipt.complete is False
    assert receipt.conflicts == ("inventory_truncated",)
    assert receipt.findings[0].kind is FindingKind.INVENTORY_INCOMPLETE
    assert not receipt.actions


def test_reconciliation_reports_closed_source_drift_without_mutation(
    tmp_path: Path,
) -> None:
    _scope(tmp_path, "194-bound", 42)
    item = _item(
        42,
        status="Active",
        state="closed",
        owner="agent-x",
        change_id="wrong-change",
    )
    invoker = FakeInvoker(inventory={"items": [item], "truncated": False})
    trigger = HousekeepingTrigger(runner=RunnerKind.WORK_MANAGEMENT_RECONCILIATION)

    receipt = asyncio.run(
        run_work_management_reconciliation(invoker, _config(tmp_path), trigger)
    )

    kinds = {finding.kind for finding in receipt.findings}
    assert FindingKind.SOURCE_CLOSED_PROJECT_ACTIVE in kinds
    assert FindingKind.STALE_EXECUTION_CLAIM in kinds
    assert FindingKind.CHANGE_PROJECTION_MISSING in kinds
    assert not receipt.actions


def test_reconciliation_suppresses_apply_when_source_scan_is_incomplete(
    tmp_path: Path,
) -> None:
    _scope(tmp_path, "194-first", 71)
    _scope(tmp_path, "194-second", 72)
    invoker = FakeInvoker(inventory={"items": [], "truncated": False})
    trigger = HousekeepingTrigger(
        runner=RunnerKind.WORK_MANAGEMENT_RECONCILIATION,
        mode=RunMode.APPLY,
        idempotency_key="bounded",
    )

    receipt = asyncio.run(
        run_work_management_reconciliation(
            invoker,
            _config(tmp_path, max_external_reads=1),
            trigger,
        )
    )

    assert receipt.complete is False
    assert "source_evidence_incomplete" in receipt.conflicts
    assert FindingKind.SOURCE_EVIDENCE_INCOMPLETE in {
        finding.kind for finding in receipt.findings
    }
    assert receipt.applied_receipts == ()


def test_backlog_readiness_promotes_mechanically_unblocked_work(
    tmp_path: Path,
) -> None:
    invoker = FakeInvoker(
        inventory={"items": [_item(51)], "truncated": False}
    )
    trigger = HousekeepingTrigger(runner=RunnerKind.BACKLOG_READINESS)

    receipt = asyncio.run(
        run_backlog_readiness(invoker, _config(tmp_path), trigger)
    )

    assert FindingKind.BLOCKED_WITHOUT_DEPENDENCY in {
        finding.kind for finding in receipt.findings
    }
    assert len(receipt.actions) == 1
    action = receipt.actions[0]
    assert action.operation == "project_management_transition_work"
    assert action.arguments["target"] == "ready"
    assert action.arguments["issue_number"] == 51


def test_backlog_readiness_reports_resolved_exact_dependency(tmp_path: Path) -> None:
    invoker = FakeInvoker(
        inventory={"items": [_item(52, blocked_by="#10")], "truncated": False}
    )
    invoker.source_states[("nielpieterse0/kis-mcp", 10)] = "closed"
    trigger = HousekeepingTrigger(runner=RunnerKind.BACKLOG_READINESS)

    receipt = asyncio.run(
        run_backlog_readiness(invoker, _config(tmp_path), trigger)
    )

    assert FindingKind.RESOLVED_DEPENDENCY_STILL_BLOCKING in {
        finding.kind for finding in receipt.findings
    }
    assert not receipt.actions


def test_backlog_readiness_reports_ambiguous_dependency_text(tmp_path: Path) -> None:
    invoker = FakeInvoker(
        inventory={
            "items": [_item(53, blocked_by="waiting for upstream approval")],
            "truncated": False,
        }
    )
    trigger = HousekeepingTrigger(runner=RunnerKind.BACKLOG_READINESS)

    receipt = asyncio.run(
        run_backlog_readiness(invoker, _config(tmp_path), trigger)
    )

    assert FindingKind.AMBIGUOUS_DEPENDENCY in {
        finding.kind for finding in receipt.findings
    }
    assert not receipt.actions


def test_backlog_readiness_fails_closed_when_selection_is_incomplete(
    tmp_path: Path,
) -> None:
    invoker = FakeInvoker(
        inventory={"items": [_item(54)], "truncated": False}
    )
    invoker.selection = {
        "selected": None,
        "evaluations": [],
        "complete": False,
        "reasons": ["inventory_truncated"],
    }
    trigger = HousekeepingTrigger(runner=RunnerKind.BACKLOG_READINESS)

    receipt = asyncio.run(
        run_backlog_readiness(invoker, _config(tmp_path), trigger)
    )

    assert receipt.complete is False
    assert "next_work_incomplete" in receipt.conflicts
    assert receipt.applied_receipts == ()


class FailingInventoryInvoker(FakeInvoker):
    async def read(
        self, operation: str, arguments: Mapping[str, Any]
    ) -> dict[str, Any]:
        if operation == "project_management_inventory":
            raise RuntimeError("provider unavailable")
        return await super().read(operation, arguments)


def test_reconciliation_returns_typed_authority_failure(tmp_path: Path) -> None:
    invoker = FailingInventoryInvoker(inventory={"items": [], "truncated": False})
    trigger = HousekeepingTrigger(runner=RunnerKind.WORK_MANAGEMENT_RECONCILIATION)

    receipt = asyncio.run(
        run_work_management_reconciliation(invoker, _config(tmp_path), trigger)
    )

    assert receipt.complete is False
    assert receipt.conflicts == ("authority_unavailable",)
    assert receipt.findings[0].kind is FindingKind.AUTHORITY_UNAVAILABLE
    assert receipt.metrics.source_failures == 1


def test_reconciliation_apply_failure_is_typed_and_incomplete(tmp_path: Path) -> None:
    _scope(tmp_path, "194-example", 364)
    invoker = FakeInvoker(inventory={"items": [], "truncated": False})
    invoker.fail_change_operation = "project_management_reconcile"
    trigger = HousekeepingTrigger(
        runner=RunnerKind.WORK_MANAGEMENT_RECONCILIATION,
        mode=RunMode.APPLY,
        idempotency_key="run-fail",
    )

    receipt = asyncio.run(
        run_work_management_reconciliation(invoker, _config(tmp_path), trigger)
    )

    assert receipt.complete is False
    assert "apply_failed" in receipt.conflicts
    assert receipt.applied_receipts == ()
    assert receipt.metrics.applied_actions == 0


def test_backlog_readiness_fails_closed_when_dependency_scan_exceeds_bound(
    tmp_path: Path,
) -> None:
    invoker = FakeInvoker(
        inventory={"items": [_item(55, blocked_by="#10,#11")], "truncated": False}
    )
    trigger = HousekeepingTrigger(runner=RunnerKind.BACKLOG_READINESS)

    receipt = asyncio.run(
        run_backlog_readiness(
            invoker,
            _config(tmp_path, max_external_reads=1),
            trigger,
        )
    )

    assert receipt.complete is False
    assert "source_evidence_incomplete" in receipt.conflicts
    assert receipt.applied_receipts == ()


def test_backlog_readiness_apply_derives_action_idempotency_key(tmp_path: Path) -> None:
    invoker = FakeInvoker(inventory={"items": [_item(56)], "truncated": False})
    trigger = HousekeepingTrigger(
        runner=RunnerKind.BACKLOG_READINESS,
        mode=RunMode.APPLY,
        idempotency_key="ready-run",
    )

    receipt = asyncio.run(
        run_backlog_readiness(invoker, _config(tmp_path), trigger)
    )

    assert receipt.metrics.applied_actions == 1
    applied = invoker.change_calls[-1][1]
    assert applied["apply"] is True
    assert applied["idempotency_key"] == "ready-run:ready:nielpieterse0/kis-mcp#56"


def test_backlog_readiness_respects_transition_gate_rejection(tmp_path: Path) -> None:
    invoker = FakeInvoker(inventory={"items": [_item(57)], "truncated": False})
    invoker.reject_ready_preview = True
    trigger = HousekeepingTrigger(runner=RunnerKind.BACKLOG_READINESS)

    receipt = asyncio.run(
        run_backlog_readiness(invoker, _config(tmp_path), trigger)
    )

    assert FindingKind.BLOCKED_WITHOUT_DEPENDENCY in {
        finding.kind for finding in receipt.findings
    }
    assert receipt.actions == ()


def test_backlog_readiness_returns_typed_authority_failure(tmp_path: Path) -> None:
    invoker = FailingInventoryInvoker(inventory={"items": [], "truncated": False})
    trigger = HousekeepingTrigger(runner=RunnerKind.BACKLOG_READINESS)

    receipt = asyncio.run(
        run_backlog_readiness(invoker, _config(tmp_path), trigger)
    )

    assert receipt.complete is False
    assert receipt.conflicts == ("authority_unavailable",)
    assert receipt.findings[0].kind is FindingKind.AUTHORITY_UNAVAILABLE
    assert receipt.metrics.source_failures == 1


def test_reconciliation_reports_duplicate_missing_source_binding(tmp_path: Path) -> None:
    _scope(tmp_path, "194-a", 80)
    _scope(tmp_path, "194-b", 80)
    invoker = FakeInvoker(inventory={"items": [], "truncated": False})
    trigger = HousekeepingTrigger(runner=RunnerKind.WORK_MANAGEMENT_RECONCILIATION)

    receipt = asyncio.run(
        run_work_management_reconciliation(invoker, _config(tmp_path), trigger)
    )

    assert FindingKind.DUPLICATE_SOURCE_BINDING in {
        finding.kind for finding in receipt.findings
    }
    assert receipt.actions == ()


def test_reconciliation_reports_duplicate_present_source_binding(tmp_path: Path) -> None:
    _scope(tmp_path, "194-a", 81)
    _scope(tmp_path, "194-b", 81)
    invoker = FakeInvoker(
        inventory={"items": [_item(81, status="Active")], "truncated": False}
    )
    trigger = HousekeepingTrigger(runner=RunnerKind.WORK_MANAGEMENT_RECONCILIATION)

    receipt = asyncio.run(
        run_work_management_reconciliation(invoker, _config(tmp_path), trigger)
    )

    assert FindingKind.DUPLICATE_SOURCE_BINDING in {
        finding.kind for finding in receipt.findings
    }
    assert receipt.actions == ()


def test_reconciliation_reports_missing_ready_metadata(tmp_path: Path) -> None:
    item = _item(82, status="Ready")
    item["field_values"] = [
        entry
        for entry in item["field_values"]
        if entry["field_name"] != "Priority"
    ]
    invoker = FakeInvoker(inventory={"items": [item], "truncated": False})
    trigger = HousekeepingTrigger(runner=RunnerKind.WORK_MANAGEMENT_RECONCILIATION)

    receipt = asyncio.run(
        run_work_management_reconciliation(invoker, _config(tmp_path), trigger)
    )

    assert FindingKind.MISSING_READY_METADATA in {
        finding.kind for finding in receipt.findings
    }


def test_backlog_readiness_does_not_promote_claimed_work(tmp_path: Path) -> None:
    invoker = FakeInvoker(
        inventory={"items": [_item(83, owner="agent-x")], "truncated": False}
    )
    trigger = HousekeepingTrigger(runner=RunnerKind.BACKLOG_READINESS)

    receipt = asyncio.run(
        run_backlog_readiness(invoker, _config(tmp_path), trigger)
    )

    assert FindingKind.BLOCKED_WITHOUT_DEPENDENCY in {
        finding.kind for finding in receipt.findings
    }
    assert receipt.actions == ()


def test_backlog_readiness_does_not_promote_closed_work(tmp_path: Path) -> None:
    invoker = FakeInvoker(
        inventory={"items": [_item(84, state="closed")], "truncated": False}
    )
    trigger = HousekeepingTrigger(runner=RunnerKind.BACKLOG_READINESS)

    receipt = asyncio.run(
        run_backlog_readiness(invoker, _config(tmp_path), trigger)
    )

    assert FindingKind.BLOCKED_WITHOUT_DEPENDENCY in {
        finding.kind for finding in receipt.findings
    }
    assert receipt.actions == ()


def test_backlog_readiness_keeps_open_dependency_blocking(tmp_path: Path) -> None:
    invoker = FakeInvoker(
        inventory={"items": [_item(85, blocked_by="#10")], "truncated": False}
    )
    invoker.source_states[("nielpieterse0/kis-mcp", 10)] = "open"
    trigger = HousekeepingTrigger(runner=RunnerKind.BACKLOG_READINESS)

    receipt = asyncio.run(
        run_backlog_readiness(invoker, _config(tmp_path), trigger)
    )

    assert FindingKind.RESOLVED_DEPENDENCY_STILL_BLOCKING not in {
        finding.kind for finding in receipt.findings
    }
    assert receipt.actions == ()


def test_reconciliation_source_read_failure_is_fail_closed(tmp_path: Path) -> None:
    _scope(tmp_path, "194-source-fail", 86)
    invoker = FakeInvoker(inventory={"items": [], "truncated": False})
    invoker.fail_sources.add(("nielpieterse0/kis-mcp", 86))
    trigger = HousekeepingTrigger(runner=RunnerKind.WORK_MANAGEMENT_RECONCILIATION)

    receipt = asyncio.run(
        run_work_management_reconciliation(invoker, _config(tmp_path), trigger)
    )

    assert receipt.complete is False
    assert "source_evidence_incomplete" in receipt.conflicts
    assert receipt.metrics.source_failures == 1
    assert receipt.actions == ()


def test_backlog_readiness_source_read_failure_is_fail_closed(tmp_path: Path) -> None:
    invoker = FakeInvoker(
        inventory={"items": [_item(87, blocked_by="#10")], "truncated": False}
    )
    invoker.fail_sources.add(("nielpieterse0/kis-mcp", 10))
    trigger = HousekeepingTrigger(runner=RunnerKind.BACKLOG_READINESS)

    receipt = asyncio.run(
        run_backlog_readiness(invoker, _config(tmp_path), trigger)
    )

    assert receipt.complete is False
    assert "source_evidence_incomplete" in receipt.conflicts
    assert receipt.metrics.source_failures == 1
    assert receipt.actions == ()


def test_backlog_readiness_apply_failure_is_typed_and_incomplete(tmp_path: Path) -> None:
    invoker = FakeInvoker(inventory={"items": [_item(88)], "truncated": False})
    invoker.fail_change_operation = "project_management_transition_work"
    trigger = HousekeepingTrigger(
        runner=RunnerKind.BACKLOG_READINESS,
        mode=RunMode.APPLY,
        idempotency_key="ready-fail",
    )

    receipt = asyncio.run(
        run_backlog_readiness(invoker, _config(tmp_path), trigger)
    )

    assert receipt.complete is False
    assert "apply_failed" in receipt.conflicts
    assert receipt.applied_receipts == ()
    assert receipt.metrics.applied_actions == 0


def test_backlog_readiness_stops_after_first_dependency_read_failure(
    tmp_path: Path,
) -> None:
    invoker = FakeInvoker(
        inventory={"items": [_item(89, blocked_by="#10,#11")], "truncated": False}
    )
    invoker.fail_sources.add(("nielpieterse0/kis-mcp", 10))
    trigger = HousekeepingTrigger(runner=RunnerKind.BACKLOG_READINESS)

    receipt = asyncio.run(
        run_backlog_readiness(invoker, _config(tmp_path), trigger)
    )

    assert receipt.complete is False
    assert "source_evidence_incomplete" in receipt.conflicts
    assert invoker.external_calls == [("nielpieterse0/kis-mcp", 10)]
