from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .command_settings import CommandPlaneSettings, load_command_plane_settings
from .contracts import WorkRecord


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


def _rank_index(value: str, ordered: tuple[str, ...], field: str) -> int:
    try:
        return ordered.index(value)
    except ValueError as exc:
        raise ValueError(f"{field} value is not configured: {value}") from exc


def _selection_key(
    record: WorkRecord, settings: CommandPlaneSettings
) -> tuple[Any, ...]:
    values: list[Any] = []
    for field in settings.queue.ranking:
        if field == "queue_rank":
            values.append(
                record.queue_rank if record.queue_rank is not None else 2**31 - 1
            )
        elif field == "priority":
            values.append(
                _rank_index(
                    record.priority.value, settings.queue.priority_order, "priority"
                )
            )
        elif field == "effort":
            values.append(
                _rank_index(record.effort.value, settings.queue.effort_order, "effort")
            )
        elif field == "created_order":
            values.append(record.created_order)
        elif field == "record_id":
            values.append(record.record_id)
        else:
            raise ValueError(f"unsupported ranking field: {field}")
    return tuple(values)


def select_next_work(
    records: tuple[WorkRecord, ...],
    *,
    project_id: str | None = None,
    completed_record_ids: tuple[str, ...] = (),
    settings: CommandPlaneSettings | None = None,
) -> WorkSelection:
    if not isinstance(records, tuple):
        raise ValueError("records must be a tuple")
    if any(not isinstance(record, WorkRecord) for record in records):
        raise ValueError("records must contain WorkRecord values")
    configured = settings or load_command_plane_settings()
    if project_id is not None:
        if not isinstance(project_id, str) or not project_id.strip():
            raise ValueError("project_id must be a non-empty string")
        project_id = project_id.strip()
    if completed_record_ids and project_id is None:
        raise ValueError("project_id is required with completed_record_ids")

    completed = {
        (record.project_id, record.record_id)
        for record in records
        if record.state is configured.completion.terminal_state
    }
    if project_id is not None:
        completed.update((project_id, record_id) for record_id in completed_record_ids)

    evaluations: list[CandidateEvaluation] = []
    eligible_records: list[WorkRecord] = []
    for record in records:
        reasons: list[str] = []
        if project_id is not None and record.project_id != project_id:
            reasons.append("project_mismatch")
        if record.state not in configured.queue.eligible_states:
            reasons.append("state_not_executable")
        if record.execution_owner is not None:
            reasons.append(f"already_claimed:{record.execution_owner}")
        if record.approval_required and not record.approval_complete:
            reasons.append("approval_incomplete")
        for dependency_id in record.dependency_ids:
            if (record.project_id, dependency_id) not in completed:
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

    selected = (
        min(eligible_records, key=lambda record: _selection_key(record, configured))
        if eligible_records
        else None
    )
    return WorkSelection(selected=selected, evaluations=tuple(evaluations))


__all__ = ["CandidateEvaluation", "WorkSelection", "select_next_work"]
