from __future__ import annotations

from kis_mcp.capabilities.contracts import OperationEffect
from kis_mcp.capabilities.surface import capability_control_contribution
from kis_mcp.projects.github_merge_queue import (
    REGISTERED_GITHUB_MERGE_QUEUE_OPERATION_SCHEMAS,
    execute_registered_github_merge_queue_operation,
)

QUEUE_OPERATIONS = {
    "kis_github_merge_queue_status",
    "kis_github_merge_queue_enqueue",
    "kis_github_merge_queue_reconcile",
    "kis_github_merge_queue_dequeue",
    "kis_github_merge_queue_land",
}


class FakeOperations:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def status(self, **kwargs):
        self.calls.append(("status", kwargs))
        return {"state": "current"}

    def enqueue(self, **kwargs):
        self.calls.append(("enqueue", kwargs))
        return {"state": "queued"}

    def reconcile(self, **kwargs):
        self.calls.append(("reconcile", kwargs))
        return {"state": "reconciled"}

    def dequeue(self, **kwargs):
        self.calls.append(("dequeue", kwargs))
        return {"state": "dequeued"}

    def land(self, **kwargs):
        self.calls.append(("land", kwargs))
        return {"state": "landed"}


def test_capability_control_exposes_bounded_merge_queue_operations() -> None:
    contribution = capability_control_contribution()
    operations = {item.name: item for item in contribution.operations}

    assert QUEUE_OPERATIONS.issubset(operations)
    assert operations["kis_github_merge_queue_status"].approval_required is False
    assert operations["kis_github_merge_queue_status"].effects == (
        OperationEffect.EXTERNAL,
        OperationEffect.READ_ONLY,
    )
    for name in QUEUE_OPERATIONS - {"kis_github_merge_queue_status"}:
        operation = operations[name]
        assert operation.approval_required is True
        assert operation.effects == (
            OperationEffect.EXTERNAL,
            OperationEffect.LOCAL_CHANGE,
        )
        assert "registered-github" in operation.tags
        assert "merge-queue" in operation.tags
        assert operation.input_schema == REGISTERED_GITHUB_MERGE_QUEUE_OPERATION_SCHEMAS[name]


def test_dispatcher_preserves_exact_queue_arguments() -> None:
    operations = FakeOperations()
    head = "1" * 40
    base = "2" * 40

    record = {"record_id": "SPEC-120"}
    trace = {"change_id": "120-kis-speculative-landing-queue"}
    governance = [{"pull_number": 167, "record": record, "trace": trace}]

    execute_registered_github_merge_queue_operation(
        "kis_github_merge_queue_enqueue",
        {
            "project_id": "kis-mcp",
            "pull_number": 167,
            "expected_head": head,
            "record": record,
            "trace": trace,
            "approved": True,
        },
        operations=operations,
    )
    execute_registered_github_merge_queue_operation(
        "kis_github_merge_queue_land",
        {
            "project_id": "kis-mcp",
            "expected_generation": 7,
            "expected_base": base,
            "governance": governance,
            "approved": True,
        },
        operations=operations,
    )

    assert operations.calls == [
        (
            "enqueue",
            {
                "project_id": "kis-mcp",
                "pull_number": 167,
                "expected_head": head,
                "record": record,
                "trace": trace,
                "approved": True,
            },
        ),
        (
            "land",
            {
                "project_id": "kis-mcp",
                "expected_generation": 7,
                "expected_base": base,
                "governance": governance,
                "approved": True,
            },
        ),
    ]
