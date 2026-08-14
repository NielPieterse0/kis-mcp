from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .backend import ProjectInventory, ProjectItem, ProjectItemKind
from .command_settings import CommandPlaneSettings, load_command_plane_settings
from .reconciliation import DesiredProjection, ObservedProjection

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


def _rank_index(value: str | None, ordered: tuple[str, ...]) -> int | None:
    if value is None:
        return None
    try:
        return ordered.index(value)
    except ValueError:
        return None


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


def _ranking_key(item: ProjectItem, settings: CommandPlaneSettings) -> tuple[Any, ...]:
    priority = _normalized_choice(_field(item, settings.queue.priority_field))
    effort = _normalized_choice(_field(item, settings.queue.effort_field))
    values: list[Any] = []
    for field in settings.queue.ranking:
        if field == "priority":
            index = _rank_index(priority, settings.queue.priority_order)
            values.append(index if index is not None else 2**31 - 1)
        elif field == "effort":
            index = _rank_index(effort, settings.queue.effort_order)
            values.append(index if index is not None else 2**31 - 1)
        elif field == "created_order":
            values.append(_created_order(item, settings))
        elif field == "record_id":
            values.append(f"{item.repository or ''}#{item.number or 0:020d}")
        else:
            raise ValueError(f"unsupported ranking field: {field}")
    return tuple(values)


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
    eligible: list[ProjectItem] = []
    for item in inventory.items:
        reasons: list[str] = []
        if item.kind is not ProjectItemKind.ISSUE:
            reasons.append("not_issue")
        if item.state is not None and item.state.casefold() != "open":
            reasons.append("source_not_open")
        state = _normalized_choice(_field(item, configured.queue.state_field))
        if state not in {
            candidate.value for candidate in configured.queue.eligible_states
        }:
            reasons.append("state_not_ready")
        priority = _normalized_choice(_field(item, configured.queue.priority_field))
        if priority not in configured.queue.priority_order:
            reasons.append(f"missing_or_invalid:{configured.queue.priority_field}")
        effort = _normalized_choice(_field(item, configured.queue.effort_field))
        if effort not in configured.queue.effort_order:
            reasons.append(f"missing_or_invalid:{configured.queue.effort_field}")
        for required_field in configured.readiness.required_project_fields:
            if required_field in {
                configured.queue.priority_field,
                configured.queue.effort_field,
            }:
                continue
            required_value = _field(item, required_field)
            if (
                required_value is _MISSING
                or required_value is None
                or (isinstance(required_value, str) and not required_value.strip())
            ):
                reasons.append(f"missing_required:{required_field}")
        owner = _field(item, configured.claim.execution_owner_field)
        if isinstance(owner, str) and owner.strip():
            reasons.append(f"already_claimed:{owner.strip()}")
        blocker = _field(item, configured.queue.blocked_by_field)
        if (
            configured.readiness.requires_dependencies_understood
            and blocker is _MISSING
        ):
            reasons.append("dependency_evidence_unavailable")
        elif blocker is not _MISSING and blocker not in (None, "", False, 0):
            reasons.append("native_dependency_blocking")

        evaluation = ProjectCandidateEvaluation(
            item_id=item.item_id,
            repository=item.repository,
            number=item.number,
            title=item.title,
            eligible=not reasons,
            reasons=tuple(reasons),
        )
        evaluations.append(evaluation)
        if evaluation.eligible:
            eligible.append(item)

    selected = (
        min(eligible, key=lambda item: _ranking_key(item, configured))
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
