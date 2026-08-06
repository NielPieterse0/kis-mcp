from __future__ import annotations

from kis_mcp.work_management import (
    LifecycleState,
    Priority,
    RecordType,
    WorkRecord,
    select_next_work,
)


def item(record_id: str, **overrides: object) -> WorkRecord:
    values: dict[str, object] = {
        "record_id": record_id,
        "project_id": "alpha-project",
        "title": record_id,
        "record_type": RecordType.TASK,
        "state": LifecycleState.APPROVED,
        "priority": Priority.MEDIUM,
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


def test_selection_prefers_active_then_priority_then_stable_order() -> None:
    records = (
        item("TASK-010", priority=Priority.CRITICAL, created_order=1),
        item(
            "TASK-011",
            state=LifecycleState.ACTIVE,
            priority=Priority.LOW,
            created_order=3,
        ),
        item(
            "TASK-012",
            state=LifecycleState.ACTIVE,
            priority=Priority.HIGH,
            created_order=8,
        ),
        item(
            "TASK-013",
            state=LifecycleState.ACTIVE,
            priority=Priority.HIGH,
            created_order=2,
        ),
    )

    result = select_next_work(records)

    assert result.selected is not None
    assert result.selected.record_id == "TASK-013"


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
    assert evaluations["TASK-041"].reasons == (
        "dependency_incomplete:TASK-040",
    )


def test_external_completed_ids_require_a_project_scope() -> None:
    import pytest

    with pytest.raises(ValueError, match="project_id"):
        select_next_work(
            (item("TASK-050", dependency_ids=("TASK-049",)),),
            completed_record_ids=("TASK-049",),
        )
