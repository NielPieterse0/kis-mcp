from __future__ import annotations

from dataclasses import dataclass

from .contracts import LifecycleState, Priority, WorkRecord

_EXECUTABLE_STATES = frozenset(
    {
        LifecycleState.APPROVED,
        LifecycleState.ACTIVE,
        LifecycleState.REVIEW,
        LifecycleState.VERIFICATION,
        LifecycleState.DOCUMENTATION,
    }
)
_STATE_ORDER = {
    LifecycleState.ACTIVE: 0,
    LifecycleState.REVIEW: 1,
    LifecycleState.VERIFICATION: 2,
    LifecycleState.DOCUMENTATION: 3,
    LifecycleState.APPROVED: 4,
}
_PRIORITY_ORDER = {
    Priority.CRITICAL: 0,
    Priority.HIGH: 1,
    Priority.MEDIUM: 2,
    Priority.LOW: 3,
}


@dataclass(frozen=True, slots=True)
class CandidateEvaluation:
    record_id: str
    project_id: str
    eligible: bool
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class WorkSelection:
    selected: WorkRecord | None
    evaluations: tuple[CandidateEvaluation, ...]


def _selection_key(record: WorkRecord) -> tuple[int, int, int, str]:
    return (
        _STATE_ORDER[record.state],
        _PRIORITY_ORDER[record.priority],
        record.created_order,
        record.record_id,
    )


def select_next_work(
    records: tuple[WorkRecord, ...],
    *,
    project_id: str | None = None,
    completed_record_ids: tuple[str, ...] = (),
) -> WorkSelection:
    if not isinstance(records, tuple):
        raise ValueError("records must be a tuple")
    if any(not isinstance(record, WorkRecord) for record in records):
        raise ValueError("records must contain WorkRecord values")
    if project_id is not None:
        if not isinstance(project_id, str) or not project_id.strip():
            raise ValueError("project_id must be a non-empty string")
        project_id = project_id.strip()

    completed = set(completed_record_ids)
    completed.update(
        record.record_id for record in records if record.state is LifecycleState.DONE
    )
    evaluations: list[CandidateEvaluation] = []
    eligible_records: list[WorkRecord] = []

    for record in records:
        reasons: list[str] = []
        if project_id is not None and record.project_id != project_id:
            reasons.append("project_mismatch")
        if record.state not in _EXECUTABLE_STATES:
            reasons.append("state_not_executable")
        if record.approval_required and not record.approval_complete:
            reasons.append("approval_incomplete")
        for dependency_id in record.dependency_ids:
            if dependency_id not in completed:
                reasons.append(f"dependency_incomplete:{dependency_id}")

        eligible = not reasons
        evaluations.append(
            CandidateEvaluation(
                record_id=record.record_id,
                project_id=record.project_id,
                eligible=eligible,
                reasons=tuple(reasons),
            )
        )
        if eligible:
            eligible_records.append(record)

    selected = min(eligible_records, key=_selection_key) if eligible_records else None
    return WorkSelection(selected=selected, evaluations=tuple(evaluations))


__all__ = [
    "CandidateEvaluation",
    "WorkSelection",
    "select_next_work",
]
