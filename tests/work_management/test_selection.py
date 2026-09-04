from __future__ import annotations

from kis_mcp.work_management import (
    DeliveryStage,
    Effort,
    LifecycleState,
    Priority,
    RecordType,
    WorkRecord,
    SelectionFacts,
    select_next_work,
    selection_tier,
)


def item(record_id: str, **overrides: object) -> WorkRecord:
    values: dict[str, object] = {
        "record_id": record_id,
        "project_id": "alpha-project",
        "title": record_id,
        "record_type": RecordType.TASK,
        "state": LifecycleState.READY,
        "priority": Priority.MEDIUM,
        "effort": Effort.MEDIUM,
    }
    values.update(overrides)
    return WorkRecord(**values)  # type: ignore[arg-type]


def test_selection_is_project_scoped_and_explains_exclusions() -> None:
    records = (
        item("TASK-001", project_id="beta-project", priority=Priority.CRITICAL),
        item("TASK-002", state=LifecycleState.ON_HOLD),
        item("TASK-003", approval_required=True, approval_complete=False),
        item("TASK-004", dependency_ids=("TASK-099",)),
        item("TASK-005", priority=Priority.HIGH),
    )

    result = select_next_work(records, project_id="alpha-project")

    assert result.selected is not None
    assert result.selected.record_id == "TASK-005"
    reasons = {item.record_id: item.reasons for item in result.evaluations}
    assert reasons["TASK-001"] == ("project_mismatch",)
    assert reasons["TASK-002"] == ("state_not_executable",)
    assert reasons["TASK-003"] == ("approval_incomplete",)
    assert reasons["TASK-004"] == ("dependency_incomplete:TASK-099",)


def test_selection_prefers_priority_then_effort_and_age() -> None:
    records = (
        item(
            "TASK-010", priority=Priority.CRITICAL, effort=Effort.LARGE, created_order=1
        ),
        item("TASK-011", priority=Priority.HIGH, effort=Effort.TINY, created_order=3),
        item(
            "TASK-012", priority=Priority.CRITICAL, effort=Effort.TINY, created_order=8
        ),
        item(
            "TASK-013",
            state=LifecycleState.ACTIVE,
            priority=Priority.CRITICAL,
            effort=Effort.TINY,
        ),
    )

    result = select_next_work(records)

    assert result.selected is not None
    assert result.selected.record_id == "TASK-012"
    reasons = {entry.record_id: entry.reasons for entry in result.evaluations}
    assert reasons["TASK-013"] == ("state_not_executable",)


def test_selection_excludes_already_claimed_ready_work() -> None:
    records = (
        item(
            "TASK-014", priority=Priority.CRITICAL, execution_owner="kis-dev/session-a"
        ),
        item("TASK-015", priority=Priority.HIGH),
    )

    result = select_next_work(records)

    assert result.selected is not None
    assert result.selected.record_id == "TASK-015"
    reasons = {entry.record_id: entry.reasons for entry in result.evaluations}
    assert reasons["TASK-014"] == ("already_claimed:kis-dev/session-a",)


def test_done_records_satisfy_dependencies() -> None:
    records = (
        item("TASK-020", state=LifecycleState.DONE),
        item("TASK-021", dependency_ids=("TASK-020",), priority=Priority.HIGH),
    )

    result = select_next_work(records)

    assert result.selected is not None
    assert result.selected.record_id == "TASK-021"


def test_selection_returns_none_when_no_record_is_executable() -> None:
    result = select_next_work((item("TASK-030", state=LifecycleState.DEFERRED),))

    assert result.selected is None
    assert result.evaluations[0].eligible is False


def test_dependency_completion_is_scoped_to_the_same_project() -> None:
    records = (
        item("TASK-040", project_id="beta-project", state=LifecycleState.DONE),
        item(
            "TASK-041",
            project_id="alpha-project",
            dependency_ids=("TASK-040",),
        ),
    )

    result = select_next_work(records, project_id="alpha-project")

    assert result.selected is None
    evaluations = {item.record_id: item for item in result.evaluations}
    assert evaluations["TASK-041"].reasons == ("dependency_incomplete:TASK-040",)


def test_external_completed_ids_require_a_project_scope() -> None:
    import pytest

    with pytest.raises(ValueError, match="project_id"):
        select_next_work(
            (item("TASK-050", dependency_ids=("TASK-049",)),),
            completed_record_ids=("TASK-049",),
        )


def test_selection_tiers_outrank_cross_tier_priority_and_effort() -> None:
    records = (
        item("TASK-060", priority=Priority.CRITICAL, effort=Effort.TINY),
        item(
            "FIND-061",
            record_type=RecordType.FINDING,
            priority=Priority.LOW,
            effort=Effort.LARGE,
        ),
        item(
            "BUG-062",
            record_type=RecordType.DEFECT,
            priority=Priority.LOW,
            effort=Effort.LARGE,
        ),
    )

    result = select_next_work(
        records, severity_by_record_id={("alpha-project", "FIND-061"): "High"}
    )

    assert result.selected is not None
    assert result.selected.record_id == "BUG-062"
    tiers = {entry.record_id: entry.selection_tier for entry in result.evaluations}
    assert tiers == {
        "TASK-060": "new",
        "FIND-061": "material_finding",
        "BUG-062": "defect",
    }


def test_material_finding_requires_material_severity() -> None:
    base = dict(
        candidate_id="FIND-080",
        project_id="alpha-project",
        state="ready",
        priority="medium",
        effort="medium",
        created_order=1,
        stable_id="FIND-080",
        record_type="finding",
    )

    assert selection_tier(SelectionFacts(**base, severity="high")) == "material_finding"
    assert selection_tier(SelectionFacts(**base, severity="low")) == "new"
    assert selection_tier(SelectionFacts(**base, severity=None)) == "new"


def test_unfinished_tier_precedes_new_and_keeps_intra_tier_ranking() -> None:
    records = (
        item("TASK-070", priority=Priority.CRITICAL, effort=Effort.TINY),
        item(
            "TASK-071",
            delivery_stage=DeliveryStage.IMPLEMENTING,
            priority=Priority.HIGH,
            effort=Effort.SMALL,
            created_order=10,
        ),
        item(
            "TASK-072",
            delivery_stage=DeliveryStage.CHANGE_CREATED,
            priority=Priority.HIGH,
            effort=Effort.TINY,
            created_order=20,
        ),
    )

    result = select_next_work(records)

    assert result.selected is not None
    assert result.selected.record_id == "TASK-072"


def test_material_finding_outranks_unfinished_and_new_work() -> None:
    records = (
        item("FIND-090", record_type=RecordType.FINDING, priority=Priority.LOW),
        item("TASK-091", delivery_stage=DeliveryStage.IMPLEMENTING, priority=Priority.CRITICAL),
        item("TASK-092", priority=Priority.CRITICAL, effort=Effort.TINY),
    )

    result = select_next_work(
        records, severity_by_record_id={("alpha-project", "FIND-090"): "Medium"}
    )

    assert result.selected is not None
    assert result.selected.record_id == "FIND-090"


def test_normalized_severity_evidence_is_project_scoped() -> None:
    records = (
        item("FIND-100", project_id="alpha-project", record_type=RecordType.FINDING,
             priority=Priority.LOW),
        item("FIND-100", project_id="beta-project", record_type=RecordType.FINDING,
             priority=Priority.CRITICAL),
    )

    result = select_next_work(
        records,
        severity_by_record_id={("alpha-project", "FIND-100"): "High"},
    )

    assert result.selected is not None
    assert result.selected.project_id == "alpha-project"
    tiers = {(entry.project_id, entry.record_id): entry.selection_tier for entry in result.evaluations}
    assert tiers[("alpha-project", "FIND-100")] == "material_finding"
    assert tiers[("beta-project", "FIND-100")] == "new"
