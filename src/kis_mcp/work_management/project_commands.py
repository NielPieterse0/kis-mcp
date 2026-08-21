from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .backend import ProjectInventory, ProjectItem, ProjectItemKind
from .command_settings import CommandPlaneSettings, load_command_plane_settings
from .reconciliation import DesiredProjection, ObservedProjection
from .selection import SelectionFacts, evaluate_selection_facts, selection_rank_key

_MISSING = object()


def _field(item: ProjectItem, name: str) -> object:
    target = name.casefold()
    for value in item.field_values:
        if value.field_name.casefold() == target:
            return value.value
    return _MISSING


def _normalized_choice(value: object) -> str | None:
    if value is _MISSING or value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip().casefold().replace(" ", "_").replace("-", "_")


def _created_order(item: ProjectItem, settings: CommandPlaneSettings) -> float:
    value = _field(item, settings.queue.created_field)
    if isinstance(value, str) and value.strip():
        try:
            return datetime.fromisoformat(
                value.strip().replace("Z", "+00:00")
            ).timestamp()
        except ValueError:
            pass
    return 10_000_000_000.0 + float(item.number or 0)


@dataclass(frozen=True, slots=True)
class ProjectCandidateEvaluation:
    item_id: str
    repository: str | None
    number: int | None
    title: str
    eligible: bool
    reasons: tuple[str, ...]

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "repository": self.repository,
            "number": self.number,
            "title": self.title,
            "eligible": self.eligible,
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True, slots=True)
class ProjectWorkSelection:
    selected: ProjectItem | None
    evaluations: tuple[ProjectCandidateEvaluation, ...]
    dependency_evidence: str
    complete: bool = True
    reasons: tuple[str, ...] = ()

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "selected": self.selected.to_json_dict()
            if self.selected is not None
            else None,
            "evaluations": [entry.to_json_dict() for entry in self.evaluations],
            "dependency_evidence": self.dependency_evidence,
            "complete": self.complete,
            "reasons": list(self.reasons),
        }


def _dependency_evidence(items: tuple[ProjectItem, ...], field_name: str) -> str:
    observed = sum(1 for item in items if _field(item, field_name) is not _MISSING)
    if observed == 0:
        return "unavailable"
    if observed == len(items):
        return "observed"
    return "partial"


def _selection_facts(item: ProjectItem, settings: CommandPlaneSettings) -> SelectionFacts:
    required_missing: list[str] = []
    for required_field in settings.readiness.required_project_fields:
        if required_field in {
            settings.queue.priority_field,
            settings.queue.effort_field,
        }:
            continue
        required_value = _field(item, required_field)
        if (
            required_value is _MISSING
            or required_value is None
            or (isinstance(required_value, str) and not required_value.strip())
        ):
            required_missing.append(required_field)

    owner_value = _field(item, settings.claim.execution_owner_field)
    owner = owner_value.strip() if isinstance(owner_value, str) and owner_value.strip() else None
    blocker = _field(item, settings.queue.blocked_by_field)
    blockers = (
        (str(blocker),)
        if blocker is not _MISSING and blocker not in (None, "", False, 0)
        else ()
    )
    return SelectionFacts(
        candidate_id=item.item_id,
        project_id=item.repository or "",
        state=_normalized_choice(_field(item, settings.queue.state_field)),
        priority=_normalized_choice(_field(item, settings.queue.priority_field)),
        effort=_normalized_choice(_field(item, settings.queue.effort_field)),
        created_order=_created_order(item, settings),
        stable_id=f"{item.repository or ''}#{item.number or 0:020d}",
        source_issue=item.kind is ProjectItemKind.ISSUE,
        source_open=item.state is None or item.state.casefold() == "open",
        claimed_owner=owner,
        required_fields_missing=tuple(required_missing),
        dependency_evidence_required=settings.readiness.requires_dependencies_understood,
        dependency_evidence_available=blocker is not _MISSING,
        dependency_blockers=blockers,
    )


def select_next_project_item(
    inventory: ProjectInventory,
    *,
    settings: CommandPlaneSettings | None = None,
) -> ProjectWorkSelection:
    if not isinstance(inventory, ProjectInventory):
        raise ValueError("inventory must be a ProjectInventory")
    configured = settings or load_command_plane_settings()
    dependency_evidence = _dependency_evidence(
        inventory.items, configured.queue.blocked_by_field
    )
    if inventory.truncated:
        return ProjectWorkSelection(
            selected=None,
            evaluations=(),
            dependency_evidence=dependency_evidence,
            complete=False,
            reasons=("inventory_truncated",),
        )

    evaluations: list[ProjectCandidateEvaluation] = []
    eligible: list[tuple[ProjectItem, SelectionFacts]] = []
    for item in inventory.items:
        facts = _selection_facts(item, configured)
        decision = evaluate_selection_facts(facts, profile="provider_project")
        evaluation = ProjectCandidateEvaluation(
            item_id=item.item_id,
            repository=item.repository,
            number=item.number,
            title=item.title,
            eligible=decision.eligible,
            reasons=decision.reasons,
        )
        evaluations.append(evaluation)
        if evaluation.eligible:
            eligible.append((item, facts))

    selected = (
        min(eligible, key=lambda pair: selection_rank_key(pair[1]))[0]
        if eligible
        else None
    )
    return ProjectWorkSelection(
        selected=selected,
        evaluations=tuple(evaluations),
        dependency_evidence=dependency_evidence,
    )


def build_item_projections(
    project_id: str,
    item: ProjectItem,
    desired_fields: dict[str, Any],
) -> tuple[DesiredProjection, ObservedProjection]:
    if item.repository is None or item.number is None:
        raise ValueError("Project item requires repository and source number")
    if item.kind not in {ProjectItemKind.ISSUE, ProjectItemKind.PULL_REQUEST}:
        raise ValueError("Project item must be an issue or pull request")
    record_id = f"WORK-{item.number}"
    source_kind = "issue" if item.kind is ProjectItemKind.ISSUE else "pull_request"
    desired = DesiredProjection(
        project_id=project_id,
        record_id=record_id,
        fields=tuple(sorted(desired_fields.items())),
        expected_revision=item.revision,
        source_repository=item.repository,
        source_number=item.number,
        source_kind=source_kind,
    )
    observed = ObservedProjection(
        project_id=project_id,
        record_id=record_id,
        fields=tuple((value.field_name, value.value) for value in item.field_values),
        revision=item.revision,
        external_id=item.item_id,
        accessible=True,
    )
    return desired, observed


def find_issue_item(
    inventory: ProjectInventory,
    repository: str,
    issue_number: int,
) -> ProjectItem:
    matches = tuple(
        item
        for item in inventory.items
        if item.kind is ProjectItemKind.ISSUE
        and item.repository is not None
        and item.repository.casefold() == repository.casefold()
        and item.number == issue_number
    )
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValueError("multiple Project items match the source issue")
    if inventory.truncated:
        raise ValueError("source issue was not found in truncated Project inventory")
    raise ValueError("source issue is not present in the Project")


__all__ = [
    "ProjectCandidateEvaluation",
    "ProjectWorkSelection",
    "build_item_projections",
    "find_issue_item",
    "select_next_project_item",
]
