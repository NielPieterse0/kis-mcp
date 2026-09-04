from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .canonical_contracts import WorkSelectionContract, load_canonical_work_contracts
from .command_settings import CommandPlaneSettings, load_command_plane_settings
from .contracts import WorkRecord


@dataclass(frozen=True, slots=True)
class CandidateEvaluation:
    record_id: str
    project_id: str
    eligible: bool
    selection_tier: str
    operator_directed: bool = False
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class WorkSelection:
    selected: WorkRecord | None
    evaluations: tuple[CandidateEvaluation, ...]


@dataclass(frozen=True, slots=True)
class SelectionFacts:
    candidate_id: str
    project_id: str
    state: str | None
    priority: str | None
    effort: str | None
    created_order: int | float
    stable_id: str
    record_type: str | None = None
    severity: str | None = None
    origin: str | None = None
    delivery_stage: str | None = None
    change_id: str | None = None
    source_issue: bool = True
    source_open: bool = True
    project_match: bool = True
    claimed_owner: str | None = None
    required_fields_missing: tuple[str, ...] = ()
    approval_required: bool = False
    approval_complete: bool = True
    dependency_evidence_required: bool = False
    dependency_evidence_available: bool = True
    dependency_blockers: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SelectionFactsDecision:
    eligible: bool
    reasons: tuple[str, ...]
    rule_ids: tuple[str, ...]


def _reason_for(contract: WorkSelectionContract, profile_id: str, kind: str) -> str | None:
    override = contract.profile(profile_id).reason(kind)
    return override if override is not None else contract.rule(kind).reason_code


def _format_reason(template: str, *, facts: SelectionFacts, field: str | None = None, dependency_id: str | None = None) -> str:
    return template.format(
        owner=facts.claimed_owner or "",
        field=field or "",
        dependency_id=dependency_id or "",
    )


def evaluate_selection_facts(
    facts: SelectionFacts,
    *,
    profile: str,
    contract: WorkSelectionContract | None = None,
) -> SelectionFactsDecision:
    configured = contract or load_canonical_work_contracts().selection
    selected_profile = configured.profile(profile)
    field_names = dict(configured.fields)
    reasons: list[str] = []
    rule_ids: list[str] = []

    def add(kind: str, *, field: str | None = None, dependency_id: str | None = None) -> None:
        template = _reason_for(configured, profile, kind)
        if template is None:
            return
        reasons.append(_format_reason(template, facts=facts, field=field, dependency_id=dependency_id))
        rule_ids.append(configured.rule(kind).rule_id)

    for kind in selected_profile.rules:
        if kind == "source_issue" and not facts.source_issue:
            add(kind)
        elif kind == "source_open" and not facts.source_open:
            add(kind)
        elif kind == "project_match" and not facts.project_match:
            add(kind)
        elif kind == "eligible_state" and facts.state not in configured.eligible_states:
            add(kind)
        elif kind == "valid_priority" and facts.priority not in configured.priority_order:
            add(kind, field=field_names["priority"])
        elif kind == "valid_effort" and facts.effort not in configured.effort_order:
            add(kind, field=field_names["effort"])
        elif kind == "required_fields":
            for missing in facts.required_fields_missing:
                add(kind, field=missing)
        elif kind == "unclaimed" and facts.claimed_owner is not None:
            add(kind)
        elif kind == "approval_complete" and facts.approval_required and not facts.approval_complete:
            add(kind)
        elif kind == "dependency_evidence" and facts.dependency_evidence_required and not facts.dependency_evidence_available:
            add(kind)
        elif kind == "dependencies_clear" and facts.dependency_blockers:
            template = _reason_for(configured, profile, kind)
            if template and "{dependency_id}" in template:
                for blocker in facts.dependency_blockers:
                    add(kind, dependency_id=blocker)
            else:
                add(kind)
    return SelectionFactsDecision(not reasons, tuple(reasons), tuple(rule_ids))


def selection_tier(
    facts: SelectionFacts,
    contract: WorkSelectionContract | None = None,
) -> str:
    configured = contract or load_canonical_work_contracts().selection
    record_type = (facts.record_type or "").casefold()
    if record_type == "defect":
        return "defect"
    if (
        record_type in {"finding", "security_finding"}
        and (facts.severity or "").casefold() in configured.material_finding_severity
    ):
        return "material_finding"
    stage = (facts.delivery_stage or "").casefold()
    if (facts.change_id and facts.change_id.strip()) or stage not in {"", "none", "complete"}:
        return "unfinished"
    return "new"


def is_operator_directed(
    facts: SelectionFacts,
    contract: WorkSelectionContract | None = None,
) -> bool:
    configured = contract or load_canonical_work_contracts().selection
    return (facts.origin or "").casefold() == configured.operator_origin


def selection_rank_key(
    facts: SelectionFacts,
    contract: WorkSelectionContract | None = None,
) -> tuple[Any, ...]:
    configured = contract or load_canonical_work_contracts().selection
    values: list[Any] = [configured.selection_tiers.index(selection_tier(facts, configured))]
    for field in configured.ranking:
        if field == "priority":
            values.append(configured.priority_order.index(facts.priority) if facts.priority in configured.priority_order else 2**31 - 1)
        elif field == "effort":
            values.append(configured.effort_order.index(facts.effort) if facts.effort in configured.effort_order else 2**31 - 1)
        elif field == "created_order":
            values.append(facts.created_order)
        elif field == "record_id":
            values.append(facts.stable_id)
        else:
            raise ValueError(f"unsupported canonical ranking field: {field}")
    return tuple(values)


def _selection_facts_for_record(
    record: WorkRecord,
    *,
    project_id: str | None,
    completed: set[tuple[str, str]],
    severity: str | None = None,
    origin: str | None = None,
) -> SelectionFacts:
    blockers = tuple(
        dependency_id
        for dependency_id in record.dependency_ids
        if (record.project_id, dependency_id) not in completed
    )
    return SelectionFacts(
        candidate_id=record.record_id,
        project_id=record.project_id,
        state=record.state.value,
        priority=record.priority.value,
        effort=record.effort.value,
        created_order=record.created_order,
        stable_id=record.record_id,
        record_type=record.record_type.value,
        severity=severity,
        origin=origin,
        delivery_stage=record.delivery_stage.value,
        project_match=project_id is None or record.project_id == project_id,
        claimed_owner=record.execution_owner,
        approval_required=record.approval_required,
        approval_complete=record.approval_complete,
        dependency_blockers=blockers,
    )


def select_next_work(
    records: tuple[WorkRecord, ...],
    *,
    project_id: str | None = None,
    completed_record_ids: tuple[str, ...] = (),
    severity_by_record_id: Mapping[tuple[str, str], str] | None = None,
    origin_by_record_id: Mapping[tuple[str, str], str] | None = None,
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

    contracts = load_canonical_work_contracts()
    canonical = contracts.selection
    severities = dict(severity_by_record_id or {})
    origins = dict(origin_by_record_id or {})
    evaluations: list[CandidateEvaluation] = []
    eligible: list[tuple[WorkRecord, SelectionFacts]] = []
    for record in records:
        facts = _selection_facts_for_record(
            record,
            project_id=project_id,
            completed=completed,
            severity=contracts.work_item.vocabulary_token(
                "severity", severities.get((record.project_id, record.record_id))
            ),
            origin=contracts.work_item.vocabulary_token(
                "origin", origins.get((record.project_id, record.record_id))
            ),
        )
        decision = evaluate_selection_facts(
            facts, profile="normalized_domain", contract=canonical
        )
        evaluations.append(
            CandidateEvaluation(
                record_id=record.record_id,
                project_id=record.project_id,
                eligible=decision.eligible,
                selection_tier=selection_tier(facts, canonical),
                operator_directed=is_operator_directed(facts, canonical),
                reasons=decision.reasons,
            )
        )
        if decision.eligible:
            eligible.append((record, facts))

    selected = (
        min(eligible, key=lambda pair: selection_rank_key(pair[1], canonical))[0]
        if eligible
        else None
    )
    return WorkSelection(selected=selected, evaluations=tuple(evaluations))


__all__ = [
    "CandidateEvaluation",
    "SelectionFacts",
    "SelectionFactsDecision",
    "WorkSelection",
    "evaluate_selection_facts",
    "is_operator_directed",
    "select_next_work",
    "selection_rank_key",
    "selection_tier",
]
