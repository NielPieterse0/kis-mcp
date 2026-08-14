from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import RLock
from typing import Any

from .backend import ProjectInventory, ProjectItem, ProjectItemKind
from .command_settings import CommandPlaneSettings, load_command_plane_settings
from .contracts import LifecycleState
from .project_commands import select_next_project_item

_MISSING = object()
_TERMINAL_OR_DEFERRED = {
    LifecycleState.DONE.value,
    LifecycleState.REJECTED.value,
    LifecycleState.SUPERSEDED.value,
    LifecycleState.DEFERRED.value,
}
_STATE_ORDER = {
    state: index
    for index, state in enumerate(
        (
            LifecycleState.ACTIVE.value,
            LifecycleState.REVIEW.value,
            LifecycleState.VERIFICATION.value,
            LifecycleState.DOCUMENTATION.value,
            LifecycleState.BLOCKED.value,
            LifecycleState.ON_HOLD.value,
            LifecycleState.READY.value,
            LifecycleState.APPROVED.value,
            LifecycleState.PROPOSED.value,
            LifecycleState.TRIAGE.value,
            LifecycleState.INBOX.value,
            LifecycleState.DEFERRED.value,
            LifecycleState.DONE.value,
            LifecycleState.REJECTED.value,
            LifecycleState.SUPERSEDED.value,
        )
    )
}
_PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _field(item: ProjectItem, name: str) -> object:
    target = name.casefold()
    for value in item.field_values:
        if value.field_name.casefold() == target:
            return value.value
    return _MISSING


def _text(value: object) -> str | None:
    if value is _MISSING or value is None:
        return None
    text = str(value).strip()
    return text or None


def _choice(value: object) -> str | None:
    text = _text(value)
    if text is None:
        return None
    return text.casefold().replace(" ", "_").replace("-", "_")


def board_field_names(
    settings: CommandPlaneSettings | None = None,
) -> tuple[str, ...]:
    configured = settings or load_command_plane_settings()
    return tuple(
        dict.fromkeys(
            (
                configured.queue.state_field,
                configured.queue.priority_field,
                configured.queue.effort_field,
                configured.queue.blocked_by_field,
                configured.claim.execution_owner_field,
                "Record Type",
                "Change ID",
                "Delivery Stage",
                "Verification",
                "Complexity",
                "Risk Triggers",
                "Authority Revision",
                "Repository",
            )
        )
    )


@dataclass(frozen=True, slots=True)
class WorkBoardCard:
    item_id: str
    project_id: str
    repository: str | None
    number: int | None
    title: str
    source_state: str | None
    work_state: str | None
    execution_owner: str | None
    priority: str | None
    effort: str | None
    record_type: str | None
    change_id: str | None
    delivery_stage: str | None
    verification: str | None
    blocked_by: str | None
    complexity: str | None
    risk_triggers: str | None
    authority_revision: str | None
    url: str | None

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "project_id": self.project_id,
            "repository": self.repository,
            "number": self.number,
            "title": self.title,
            "source_state": self.source_state,
            "work_state": self.work_state,
            "execution_owner": self.execution_owner,
            "priority": self.priority,
            "effort": self.effort,
            "record_type": self.record_type,
            "change_id": self.change_id,
            "delivery_stage": self.delivery_stage,
            "verification": self.verification,
            "blocked_by": self.blocked_by,
            "complexity": self.complexity,
            "risk_triggers": self.risk_triggers,
            "authority_revision": self.authority_revision,
            "url": self.url,
        }


@dataclass(frozen=True, slots=True)
class CurrentWorkSelection:
    project_id: str
    execution_owner: str
    status: str
    complete: bool
    selected: WorkBoardCard | None
    candidates: tuple[WorkBoardCard, ...]
    reasons: tuple[str, ...] = ()
    next_actions: tuple[str, ...] = ()

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "execution_owner": self.execution_owner,
            "status": self.status,
            "complete": self.complete,
            "selected": self.selected.to_json_dict() if self.selected else None,
            "candidates": [item.to_json_dict() for item in self.candidates],
            "reasons": list(self.reasons),
            "next_actions": list(self.next_actions),
        }


@dataclass(frozen=True, slots=True)
class WorkBoardSnapshot:
    project_id: str
    repository: str | None
    observed_at: str
    authority: str
    complete: bool
    truncated: bool
    next_cursor: str | None
    include_history: bool
    cards: tuple[WorkBoardCard, ...]
    state_counts: tuple[tuple[str, int], ...]
    groups: tuple[tuple[str, tuple[str, ...]], ...]
    next_eligible_item_id: str | None
    query: str | None = None
    owner: str | None = None
    states: tuple[str, ...] = ()
    schema_version: int = 1

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "project_id": self.project_id,
            "repository": self.repository,
            "observed_at": self.observed_at,
            "authority": self.authority,
            "complete": self.complete,
            "truncated": self.truncated,
            "next_cursor": self.next_cursor,
            "include_history": self.include_history,
            "filters": {
                "query": self.query,
                "owner": self.owner,
                "states": list(self.states),
            },
            "state_counts": dict(self.state_counts),
            "groups": {name: list(item_ids) for name, item_ids in self.groups},
            "next_eligible_item_id": self.next_eligible_item_id,
            "cards": [card.to_json_dict() for card in self.cards],
        }


def _card(
    project_id: str,
    item: ProjectItem,
    settings: CommandPlaneSettings,
) -> WorkBoardCard:
    return WorkBoardCard(
        item_id=item.item_id,
        project_id=project_id,
        repository=item.repository,
        number=item.number,
        title=item.title,
        source_state=item.state,
        work_state=_choice(_field(item, settings.queue.state_field)),
        execution_owner=_text(_field(item, settings.claim.execution_owner_field)),
        priority=_choice(_field(item, settings.queue.priority_field)),
        effort=_choice(_field(item, settings.queue.effort_field)),
        record_type=_choice(_field(item, "Record Type")),
        change_id=_text(_field(item, "Change ID")),
        delivery_stage=_choice(_field(item, "Delivery Stage")),
        verification=_choice(_field(item, "Verification")),
        blocked_by=_text(_field(item, settings.queue.blocked_by_field)),
        complexity=_choice(_field(item, "Complexity")),
        risk_triggers=_text(_field(item, "Risk Triggers")),
        authority_revision=_text(_field(item, "Authority Revision")) or item.revision,
        url=item.url,
    )


def _sort_key(card: WorkBoardCard) -> tuple[Any, ...]:
    return (
        _STATE_ORDER.get(card.work_state or "", 2**31 - 1),
        _PRIORITY_ORDER.get(card.priority or "", 2**31 - 1),
        (card.repository or "").casefold(),
        card.number or 2**31 - 1,
        card.item_id,
    )


def build_work_board(
    inventory: ProjectInventory,
    project_id: str,
    *,
    include_history: bool = False,
    states: tuple[str, ...] = (),
    owner: str | None = None,
    query: str | None = None,
    group_by: str = "state",
    settings: CommandPlaneSettings | None = None,
) -> WorkBoardSnapshot:
    if not isinstance(inventory, ProjectInventory):
        raise ValueError("inventory must be a ProjectInventory")
    project = project_id.strip() if isinstance(project_id, str) else ""
    if not project:
        raise ValueError("project_id must be a non-empty string")
    configured = settings or load_command_plane_settings()
    normalized_states = tuple(
        dict.fromkeys(
            value.strip().casefold().replace(" ", "_").replace("-", "_")
            for value in states
            if isinstance(value, str) and value.strip()
        )
    )
    owner_filter = owner.strip() if isinstance(owner, str) and owner.strip() else None
    query_filter = query.strip().casefold() if isinstance(query, str) and query.strip() else None

    cards: list[WorkBoardCard] = []
    all_counts: Counter[str] = Counter()
    for item in inventory.items:
        if item.kind is not ProjectItemKind.ISSUE:
            continue
        card = _card(project, item, configured)
        if card.work_state is not None:
            all_counts[card.work_state] += 1
        if not include_history and card.work_state in _TERMINAL_OR_DEFERRED:
            continue
        if normalized_states and card.work_state not in normalized_states:
            continue
        if owner_filter is not None and (card.execution_owner or "").casefold() != owner_filter.casefold():
            continue
        if query_filter is not None:
            haystack = " ".join(
                value
                for value in (
                    card.title,
                    card.repository or "",
                    str(card.number or ""),
                    card.change_id or "",
                    card.execution_owner or "",
                )
                if value
            ).casefold()
            if query_filter not in haystack:
                continue
        cards.append(card)

    cards.sort(key=_sort_key)
    grouped: dict[str, list[str]] = defaultdict(list)
    for card in cards:
        if group_by == "state":
            key = card.work_state or "unknown"
        elif group_by == "owner":
            key = card.execution_owner or "unclaimed"
        elif group_by == "repository":
            key = card.repository or "unknown"
        else:
            raise ValueError("group_by must be one of: state, owner, repository")
        grouped[key].append(card.item_id)

    selection = select_next_project_item(inventory, settings=configured)
    return WorkBoardSnapshot(
        project_id=project,
        repository=inventory.binding.repository,
        observed_at=datetime.now(UTC).isoformat(),
        authority="configured_work_management_backend",
        complete=not inventory.truncated,
        truncated=inventory.truncated,
        next_cursor=inventory.next_cursor,
        include_history=include_history,
        cards=tuple(cards),
        state_counts=tuple(sorted(all_counts.items())),
        groups=tuple(
            (name, tuple(item_ids)) for name, item_ids in sorted(grouped.items())
        ),
        next_eligible_item_id=(
            selection.selected.item_id if selection.selected is not None else None
        ),
        query=query.strip() if isinstance(query, str) and query.strip() else None,
        owner=owner_filter,
        states=normalized_states,
    )


def select_current_work(
    inventory: ProjectInventory,
    project_id: str,
    execution_owner: str,
    *,
    settings: CommandPlaneSettings | None = None,
) -> CurrentWorkSelection:
    owner = execution_owner.strip() if isinstance(execution_owner, str) else ""
    if not owner:
        raise ValueError("execution_owner must be a non-empty string")
    configured = settings or load_command_plane_settings()
    candidates = tuple(
        sorted(
            (
                _card(project_id, item, configured)
                for item in inventory.items
                if item.kind is ProjectItemKind.ISSUE
                and _choice(_field(item, configured.queue.state_field))
                == LifecycleState.ACTIVE.value
                and (_text(_field(item, configured.claim.execution_owner_field)) or "").casefold()
                == owner.casefold()
            ),
            key=_sort_key,
        )
    )
    if inventory.truncated:
        return CurrentWorkSelection(
            project_id=project_id,
            execution_owner=owner,
            status="incomplete",
            complete=False,
            selected=None,
            candidates=candidates,
            reasons=("inventory_truncated",),
            next_actions=("project_management_current_work",),
        )
    if not candidates:
        return CurrentWorkSelection(
            project_id=project_id,
            execution_owner=owner,
            status="none",
            complete=True,
            selected=None,
            candidates=(),
            reasons=("no_active_claim",),
            next_actions=("project_management_next_work", "project_management_take_next_work"),
        )
    if len(candidates) > 1:
        return CurrentWorkSelection(
            project_id=project_id,
            execution_owner=owner,
            status="ambiguous",
            complete=True,
            selected=None,
            candidates=candidates,
            reasons=("multiple_active_claims",),
            next_actions=("project_management_board_data",),
        )
    selected = candidates[0]
    actions = [
        "project_management_board_data",
        "project_management_transition_work",
        "project_management_release_work",
    ]
    if selected.change_id:
        actions.insert(0, "inspect_change")
        actions.insert(1, "execute_change_workflow")
    return CurrentWorkSelection(
        project_id=project_id,
        execution_owner=owner,
        status="current",
        complete=True,
        selected=selected,
        candidates=candidates,
        next_actions=tuple(actions),
    )


class WorkBoardProjectionBridge:
    """Hold the latest derived board projection in memory for read-only UI reuse."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._snapshot: WorkBoardSnapshot | None = None

    def publish(self, snapshot: WorkBoardSnapshot) -> None:
        if not isinstance(snapshot, WorkBoardSnapshot):
            raise ValueError("snapshot must be a WorkBoardSnapshot")
        with self._lock:
            self._snapshot = snapshot

    def current(self) -> Mapping[str, Any]:
        with self._lock:
            snapshot = self._snapshot
        if snapshot is None:
            return {
                "schema_version": 1,
                "status": "unavailable",
                "reason": "no_authoritative_board_read_observed_in_process",
                "authority": "configured_work_management_backend",
            }
        return {"status": "available", **snapshot.to_json_dict()}


__all__ = [
    "CurrentWorkSelection",
    "WorkBoardCard",
    "WorkBoardProjectionBridge",
    "WorkBoardSnapshot",
    "board_field_names",
    "build_work_board",
    "select_current_work",
]
