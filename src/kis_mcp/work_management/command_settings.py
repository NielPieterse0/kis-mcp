from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .contracts import DeliveryStage, LifecycleState

_ALLOWED_AUTHORITIES = frozenset(
    {
        "work_management",
        "work_management_then_repository_change",
        "repository_change",
        "git",
        "github",
        "actions",
        "derived",
    }
)
_ALLOWED_DIRECTIONS = frozenset({"command", "evidence", "handoff"})
_ALLOWED_RANKING = frozenset({"priority", "effort", "created_order", "record_id"})


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def _strings(value: Any, label: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be an array")
    result = tuple(_text(item, label) for item in value)
    if len(set(result)) != len(result):
        raise ValueError(f"{label} must contain unique values")
    return result


def _boolean(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{label} must be a boolean")
    return value


@dataclass(frozen=True, slots=True)
class FieldAuthority:
    authority: str
    direction: str

    def __post_init__(self) -> None:
        if self.authority not in _ALLOWED_AUTHORITIES:
            raise ValueError(f"unsupported field authority: {self.authority}")
        if self.direction not in _ALLOWED_DIRECTIONS:
            raise ValueError(f"unsupported sync direction: {self.direction}")


@dataclass(frozen=True, slots=True)
class QueueSettings:
    state_field: str
    priority_field: str
    effort_field: str
    created_field: str
    blocked_by_field: str
    eligible_states: tuple[LifecycleState, ...]
    priority_order: tuple[str, ...]
    effort_order: tuple[str, ...]
    ranking: tuple[str, ...]

    def __post_init__(self) -> None:
        for value in (
            self.state_field,
            self.priority_field,
            self.effort_field,
            self.created_field,
            self.blocked_by_field,
        ):
            _text(value, "queue field")
        if not self.eligible_states:
            raise ValueError("queue eligible_states must not be empty")
        if len(set(self.priority_order)) != len(self.priority_order):
            raise ValueError("queue priority_order must be unique")
        if len(set(self.effort_order)) != len(self.effort_order):
            raise ValueError("queue effort_order must be unique")
        if not self.ranking or any(
            item not in _ALLOWED_RANKING for item in self.ranking
        ):
            raise ValueError("queue ranking contains unsupported values")
        if len(set(self.ranking)) != len(self.ranking):
            raise ValueError("queue ranking must be unique")


@dataclass(frozen=True, slots=True)
class ReadinessSettings:
    required_project_fields: tuple[str, ...]
    required_issue_sections: tuple[str, ...]
    requires_dependencies_understood: bool


@dataclass(frozen=True, slots=True)
class ClaimSettings:
    execution_owner_field: str
    auto_expiry: bool

    def __post_init__(self) -> None:
        _text(self.execution_owner_field, "execution_owner_field")
        if not isinstance(self.auto_expiry, bool):
            raise ValueError("auto_expiry must be a boolean")


@dataclass(frozen=True, slots=True)
class DeliverySettings:
    stage_field: str
    change_id_field: str
    complexity_field: str
    risk_triggers_field: str
    change_created_stage: DeliveryStage
    complete_stage: DeliveryStage

    def __post_init__(self) -> None:
        for value in (
            self.stage_field,
            self.change_id_field,
            self.complexity_field,
            self.risk_triggers_field,
        ):
            _text(value, "delivery field")


@dataclass(frozen=True, slots=True)
class CompletionSettings:
    terminal_state: LifecycleState
    require_no_active_claim_after_close: bool


@dataclass(frozen=True, slots=True)
class CommandPlaneSettings:
    field_authority: tuple[tuple[str, FieldAuthority], ...]
    work_states: tuple[LifecycleState, ...]
    intake_aliases: tuple[tuple[str, LifecycleState], ...]
    transitions: tuple[tuple[LifecycleState, tuple[LifecycleState, ...]], ...]
    queue: QueueSettings
    readiness: ReadinessSettings
    transition_requirements: tuple[tuple[LifecycleState, tuple[str, ...]], ...]
    claim: ClaimSettings
    delivery_stages: tuple[DeliveryStage, ...]
    delivery: DeliverySettings
    completion: CompletionSettings

    def authority(self, field_name: str) -> FieldAuthority:
        key = _text(field_name, "field_name").casefold()
        for name, spec in self.field_authority:
            if name.casefold() == key:
                return spec
        raise KeyError(field_name)

    def intake_state(self, value: str) -> LifecycleState | None:
        key = _text(value, "intake state").casefold().replace(" ", "_").replace("-", "_")
        for alias, state in self.intake_aliases:
            if alias == key:
                return state
        return None

    def transition_targets(self, state: LifecycleState) -> tuple[LifecycleState, ...]:
        for source, targets in self.transitions:
            if source is state:
                return targets
        return ()

    def required_fields_for_transition(self, state: LifecycleState) -> tuple[str, ...]:
        for target, fields in self.transition_requirements:
            if target is state:
                return fields
        return ()


def _field_authority(value: Any) -> tuple[tuple[str, FieldAuthority], ...]:
    mapping = _object(value, "field_authority")
    result: list[tuple[str, FieldAuthority]] = []
    for name, raw in mapping.items():
        spec = _object(raw, f"field_authority.{name}")
        if set(spec) != {"authority", "direction"}:
            raise ValueError(f"field_authority.{name} requires authority and direction")
        result.append(
            (
                _text(name, "field name"),
                FieldAuthority(
                    authority=_text(spec["authority"], "authority"),
                    direction=_text(spec["direction"], "direction"),
                ),
            )
        )
    names = [name.casefold() for name, _ in result]
    if len(set(names)) != len(names):
        raise ValueError("field_authority names must be unique")
    return tuple(sorted(result, key=lambda item: item[0].casefold()))


def _intake_aliases(value: Any) -> tuple[tuple[str, LifecycleState], ...]:
    mapping = _object(value, "intake_aliases")
    result: list[tuple[str, LifecycleState]] = []
    for raw_alias, raw_state in mapping.items():
        alias = _text(raw_alias, "intake alias").casefold().replace(" ", "_").replace("-", "_")
        result.append((alias, LifecycleState(_text(raw_state, f"intake_aliases.{raw_alias}"))))
    aliases = [alias for alias, _state in result]
    if len(set(aliases)) != len(aliases):
        raise ValueError("intake_aliases must contain unique aliases")
    return tuple(sorted(result, key=lambda item: item[0]))


def _transitions(
    value: Any,
) -> tuple[tuple[LifecycleState, tuple[LifecycleState, ...]], ...]:
    mapping = _object(value, "transitions")
    result: list[tuple[LifecycleState, tuple[LifecycleState, ...]]] = []
    for raw_source, raw_targets in mapping.items():
        source = LifecycleState(_text(raw_source, "transition source"))
        targets = tuple(
            LifecycleState(item)
            for item in _strings(raw_targets, f"transitions.{raw_source}")
        )
        result.append((source, targets))
    return tuple(sorted(result, key=lambda item: item[0].value))


def _transition_requirements(
    value: Any,
) -> tuple[tuple[LifecycleState, tuple[str, ...]], ...]:
    mapping = _object(value, "transition_requirements")
    result = tuple(
        (
            LifecycleState(_text(raw_state, "transition requirement state")),
            _strings(raw_fields, f"transition_requirements.{raw_state}"),
        )
        for raw_state, raw_fields in mapping.items()
    )
    return tuple(sorted(result, key=lambda item: item[0].value))


def load_command_plane_settings(path: Path | None = None) -> CommandPlaneSettings:
    target = path or (
        Path(__file__).resolve().parents[3]
        / "settings"
        / "work-management"
        / "command-plane.settings.json"
    )
    root = _object(
        json.loads(target.read_text(encoding="utf-8-sig")), "command-plane settings"
    )
    required = {
        "schema_version",
        "field_authority",
        "work_states",
        "transitions",
        "queue",
        "readiness",
        "transition_requirements",
        "claim",
        "delivery_stages",
        "delivery",
        "completion",
    }
    allowed = required | {"intake_aliases"}
    if not required.issubset(root) or not set(root).issubset(allowed):
        raise ValueError("command-plane settings keys do not match the contract")
    if root["schema_version"] != 1:
        raise ValueError("command-plane schema_version must be 1")
    queue = _object(root["queue"], "queue")
    readiness = _object(root["readiness"], "readiness")
    claim = _object(root["claim"], "claim")
    delivery = _object(root["delivery"], "delivery")
    completion = _object(root["completion"], "completion")
    settings = CommandPlaneSettings(
        field_authority=_field_authority(root["field_authority"]),
        work_states=tuple(
            LifecycleState(item)
            for item in _strings(root["work_states"], "work_states")
        ),
        intake_aliases=_intake_aliases(root.get("intake_aliases", {})),
        transitions=_transitions(root["transitions"]),
        queue=QueueSettings(
            state_field=_text(queue["state_field"], "queue.state_field"),
            priority_field=_text(queue["priority_field"], "queue.priority_field"),
            effort_field=_text(queue["effort_field"], "queue.effort_field"),
            created_field=_text(queue["created_field"], "queue.created_field"),
            blocked_by_field=_text(queue["blocked_by_field"], "queue.blocked_by_field"),
            eligible_states=tuple(
                LifecycleState(item)
                for item in _strings(queue["eligible_states"], "queue.eligible_states")
            ),
            priority_order=_strings(queue["priority_order"], "queue.priority_order"),
            effort_order=_strings(queue["effort_order"], "queue.effort_order"),
            ranking=_strings(queue["ranking"], "queue.ranking"),
        ),
        readiness=ReadinessSettings(
            required_project_fields=_strings(
                readiness["required_project_fields"],
                "readiness.required_project_fields",
            ),
            required_issue_sections=_strings(
                readiness["required_issue_sections"],
                "readiness.required_issue_sections",
            ),
            requires_dependencies_understood=_boolean(
                readiness["requires_dependencies_understood"],
                "readiness.requires_dependencies_understood",
            ),
        ),
        transition_requirements=_transition_requirements(
            root["transition_requirements"]
        ),
        claim=ClaimSettings(
            execution_owner_field=_text(
                claim["execution_owner_field"], "execution_owner_field"
            ),
            auto_expiry=claim["auto_expiry"],
        ),
        delivery_stages=tuple(
            DeliveryStage(item)
            for item in _strings(root["delivery_stages"], "delivery_stages")
        ),
        delivery=DeliverySettings(
            stage_field=_text(delivery["stage_field"], "delivery.stage_field"),
            change_id_field=_text(
                delivery["change_id_field"], "delivery.change_id_field"
            ),
            complexity_field=_text(
                delivery["complexity_field"], "delivery.complexity_field"
            ),
            risk_triggers_field=_text(
                delivery["risk_triggers_field"], "delivery.risk_triggers_field"
            ),
            change_created_stage=DeliveryStage(
                _text(delivery["change_created_stage"], "delivery.change_created_stage")
            ),
            complete_stage=DeliveryStage(
                _text(delivery["complete_stage"], "delivery.complete_stage")
            ),
        ),
        completion=CompletionSettings(
            terminal_state=LifecycleState(
                _text(completion["terminal_state"], "terminal_state")
            ),
            require_no_active_claim_after_close=_boolean(
                completion["require_no_active_claim_after_close"],
                "completion.require_no_active_claim_after_close",
            ),
        ),
    )
    declared = set(settings.work_states)
    undeclared = {
        state
        for state, targets in settings.transitions
        for state in (state, *targets)
        if state not in declared
        and state
        not in {
            LifecycleState.REVIEW,
            LifecycleState.VERIFICATION,
            LifecycleState.DOCUMENTATION,
        }
    }
    if undeclared:
        raise ValueError("transitions contain undeclared work states")
    if any(state not in declared for _alias, state in settings.intake_aliases):
        raise ValueError("intake_aliases must target declared work states")
    declared_alias_keys = {state.value.casefold() for state in declared}
    if any(alias in declared_alias_keys for alias, _state in settings.intake_aliases):
        raise ValueError("intake_aliases must not shadow declared work states")
    return settings


__all__ = [
    "ClaimSettings",
    "CommandPlaneSettings",
    "CompletionSettings",
    "DeliverySettings",
    "FieldAuthority",
    "QueueSettings",
    "ReadinessSettings",
    "load_command_plane_settings",
]
