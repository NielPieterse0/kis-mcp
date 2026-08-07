from __future__ import annotations

import asyncio

import pytest

from kis_mcp.work_management import (
    DesiredProjection,
    ObservedProjection,
    ReconciliationAction,
    ReconciliationOutcome,
    plan_reconciliation,
    run_reconciliation,
)


def desired(
    record_id: str,
    *,
    title: str = "Expected",
    expected_revision: str | None = None,
) -> DesiredProjection:
    return DesiredProjection(
        project_id="alpha-project",
        record_id=record_id,
        fields=(("Status", "Active"), ("Title", title)),
        expected_revision=expected_revision,
    )


def observed(
    record_id: str,
    *,
    title: str = "Observed",
    revision: str = "rev-1",
    accessible: bool = True,
) -> ObservedProjection:
    return ObservedProjection(
        project_id="alpha-project",
        record_id=record_id,
        fields=(("Status", "Active"), ("Title", title)),
        revision=revision,
        accessible=accessible,
    )


def test_plan_is_deterministic_and_classifies_create_update_and_noop() -> None:
    decisions = plan_reconciliation(
        (desired("TASK-2", title="Changed"), desired("TASK-1"), desired("TASK-3")),
        (observed("TASK-1", title="Expected"), observed("TASK-2")),
        supported_fields=("Status", "Title"),
    )

    assert [item.record_id for item in decisions] == ["TASK-1", "TASK-2", "TASK-3"]
    assert [item.action for item in decisions] == [
        ReconciliationAction.NOOP,
        ReconciliationAction.UPDATE,
        ReconciliationAction.CREATE,
    ]
    assert decisions[1].changed_fields == ("Title",)


def test_plan_reports_observed_records_missing_from_desired_state() -> None:
    decisions = plan_reconciliation(
        (desired("TASK-1"),),
        (
            observed("TASK-1", title="Expected"),
            observed("TASK-9", title="Orphaned"),
        ),
        supported_fields=("Status", "Title"),
    )

    assert [item.record_id for item in decisions] == ["TASK-1", "TASK-9"]
    assert decisions[1].action is ReconciliationAction.ORPHANED
    assert decisions[1].observed_revision == "rev-1"


def test_plan_reports_conflict_unsupported_and_inaccessible() -> None:
    conflict = plan_reconciliation(
        (desired("TASK-1", expected_revision="rev-old"),),
        (observed("TASK-1", revision="rev-new"),),
        supported_fields=("Status", "Title"),
    )[0]
    unsupported = plan_reconciliation(
        (desired("TASK-2"),),
        (),
        supported_fields=("Status",),
    )[0]
    inaccessible = plan_reconciliation(
        (desired("TASK-3"),),
        (observed("TASK-3", accessible=False),),
        supported_fields=("Status", "Title"),
    )[0]

    assert conflict.action is ReconciliationAction.CONFLICT
    assert conflict.observed_revision == "rev-new"
    assert unsupported.action is ReconciliationAction.UNSUPPORTED
    assert unsupported.changed_fields == ("Title",)
    assert inaccessible.action is ReconciliationAction.INACCESSIBLE


def test_plan_rejects_duplicate_desired_identity() -> None:
    with pytest.raises(ValueError, match="duplicate desired projection"):
        plan_reconciliation(
            (desired("TASK-1"), desired("TASK-1")),
            (),
            supported_fields=("Status", "Title"),
        )


class Backend:
    def __init__(self) -> None:
        self.decisions = []

    async def apply_reconciliation(
        self,
        decision,
        *,
        idempotency_key: str,
    ) -> ReconciliationOutcome:
        self.decisions.append((decision, idempotency_key))
        return ReconciliationOutcome(
            project_id=decision.project_id,
            record_id=decision.record_id,
            action=decision.action,
            applied=True,
            success=True,
            provider_revision="rev-2",
        )


def test_dry_run_returns_per_record_outcomes_without_backend_calls() -> None:
    backend = Backend()
    decisions = plan_reconciliation(
        (desired("TASK-1", title="Changed"), desired("TASK-2")),
        (observed("TASK-1"),),
        supported_fields=("Status", "Title"),
    )

    outcomes = asyncio.run(run_reconciliation(decisions, backend, apply=False))

    assert backend.decisions == []
    assert [item.applied for item in outcomes] == [False, False]
    assert [item.action for item in outcomes] == [
        ReconciliationAction.UPDATE,
        ReconciliationAction.CREATE,
    ]


def test_apply_requires_idempotency_and_applies_only_actionable_decisions() -> None:
    backend = Backend()
    decisions = plan_reconciliation(
        (desired("TASK-1", title="Expected"), desired("TASK-2")),
        (observed("TASK-1", title="Expected"),),
        supported_fields=("Status", "Title"),
    )

    with pytest.raises(ValueError, match="idempotency_key"):
        asyncio.run(run_reconciliation(decisions, backend, apply=True))

    outcomes = asyncio.run(
        run_reconciliation(
            decisions,
            backend,
            apply=True,
            idempotency_key="reconcile-001",
        )
    )

    assert len(backend.decisions) == 1
    assert backend.decisions[0][0].record_id == "TASK-2"
    assert outcomes[0].action is ReconciliationAction.NOOP
    assert outcomes[0].success is True
    assert outcomes[1].provider_revision == "rev-2"
