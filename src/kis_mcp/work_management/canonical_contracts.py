from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_ITEM_KEYS = frozenset({"schema_version", "contract_id", "contexts", "fields", "vocabularies"})
_CONTEXT_KEYS = frozenset({"id", "definition", "kind", "values"})
_FIELD_KEYS = frozenset({
    "id", "name", "provider_type", "managed", "authority", "direction",
    "definition", "vocabulary", "applicable_record_types", "required_contexts", "population",
})
_VOCABULARY_KEYS = frozenset({"id", "definition", "values"})
_VALUE_KEYS = frozenset({"token", "label", "definition"})
_LIFECYCLE_KEYS = frozenset({
    "schema_version", "contract_id", "states", "intake_aliases", "transitions",
    "readiness", "transition_requirements", "claim", "delivery", "completion",
    "guards", "operations", "verification_domains",
})
_SELECTION_KEYS = frozenset({
    "schema_version", "contract_id", "fields", "eligible_states", "priority_order",
    "effort_order", "selection_tiers", "material_finding_severity", "operator_origin",
    "ranking", "dependency_evidence", "rules", "profiles",
})


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def _array(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be an array")
    return value


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _exact_keys(value: Mapping[str, Any], expected: frozenset[str], label: str) -> None:
    if set(value) != expected:
        raise ValueError(f"{label} keys must be exactly {', '.join(sorted(expected))}")


def _unique(values: tuple[str, ...], label: str) -> tuple[str, ...]:
    if len(set(values)) != len(values):
        raise ValueError(f"{label} must contain unique values")
    return values


def _fingerprint(document: Mapping[str, Any]) -> str:
    payload = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class VocabularyValue:
    token: str
    label: str
    definition: str

    def to_json_dict(self) -> dict[str, str]:
        return {"token": self.token, "label": self.label, "definition": self.definition}


@dataclass(frozen=True, slots=True)
class VocabularyDefinition:
    vocabulary_id: str
    definition: str
    values: tuple[VocabularyValue, ...]

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "id": self.vocabulary_id,
            "definition": self.definition,
            "values": [item.to_json_dict() for item in self.values],
        }


@dataclass(frozen=True, slots=True)
class ApplicabilityContext:
    context_id: str
    definition: str
    kind: str
    values: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CanonicalField:
    field_id: str
    name: str
    provider_type: str
    managed: bool
    authority: str
    direction: str
    definition: str
    vocabulary: str | None
    applicable_record_types: tuple[str, ...]
    required_contexts: tuple[str, ...]
    population: str

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "id": self.field_id,
            "name": self.name,
            "provider_type": self.provider_type,
            "managed": self.managed,
            "authority": self.authority,
            "direction": self.direction,
            "definition": self.definition,
            "vocabulary": self.vocabulary,
            "applicable_record_types": list(self.applicable_record_types),
            "required_contexts": list(self.required_contexts),
            "population": self.population,
        }


@dataclass(frozen=True, slots=True)
class WorkItemSemanticsContract:
    schema_version: int
    contract_id: str
    contexts: tuple[ApplicabilityContext, ...]
    fields: tuple[CanonicalField, ...]
    vocabularies: tuple[VocabularyDefinition, ...]
    fingerprint: str

    @property
    def managed_fields(self) -> tuple[str, ...]:
        return tuple(item.name for item in self.fields if item.managed)

    def field(self, name: str) -> CanonicalField:
        target = _text(name, "field name").casefold()
        for item in self.fields:
            if item.name.casefold() == target:
                return item
        raise KeyError(name)

    def vocabulary(self, vocabulary_id: str) -> VocabularyDefinition:
        target = _text(vocabulary_id, "vocabulary id")
        for item in self.vocabularies:
            if item.vocabulary_id == target:
                return item
        raise KeyError(vocabulary_id)

    def vocabulary_tokens(self, vocabulary_id: str) -> tuple[str, ...]:
        return tuple(item.token for item in self.vocabulary(vocabulary_id).values)

    def vocabulary_token(self, vocabulary_id: str, value: object) -> str | None:
        if not isinstance(value, str) or not value.strip():
            return None
        normalized = value.strip().casefold().replace(" ", "_").replace("-", "_")
        for item in self.vocabulary(vocabulary_id).values:
            if normalized in {
                item.token.casefold(),
                item.label.casefold().replace(" ", "_").replace("-", "_"),
            }:
                return item.token
        return None

    def required_fields_for(
        self,
        *,
        state: str | None,
        record_type: str | None,
        signals: tuple[str, ...] = (),
    ) -> tuple[str, ...]:
        active: set[str] = set()
        signal_set = set(signals)
        for context in self.contexts:
            if context.kind == "state_in" and state in context.values:
                active.add(context.context_id)
            elif context.kind == "record_type_in" and record_type in context.values:
                active.add(context.context_id)
            elif context.kind == "signal" and signal_set.intersection(context.values):
                active.add(context.context_id)
        return tuple(
            field.name
            for field in self.fields
            if set(field.required_contexts).intersection(active)
            and (
                "*" in field.applicable_record_types
                or record_type in field.applicable_record_types
            )
        )

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "contract_id": self.contract_id,
            "contexts": [
                {
                    "id": item.context_id,
                    "definition": item.definition,
                    "kind": item.kind,
                    "values": list(item.values),
                }
                for item in self.contexts
            ],
            "fields": [item.to_json_dict() for item in self.fields],
            "vocabularies": [item.to_json_dict() for item in self.vocabularies],
        }


@dataclass(frozen=True, slots=True)
class LifecycleStateDefinition:
    token: str
    label: str
    definition: str
    project_status: bool


@dataclass(frozen=True, slots=True)
class LifecycleGuard:
    rule_id: str
    target: str
    condition: str
    reason_code: str
    definition: str
    disposition: str


@dataclass(frozen=True, slots=True)
class LifecycleOperation:
    operation_id: str
    effect: str
    implementation_surface: str
    definition: str


@dataclass(frozen=True, slots=True)
class WorkLifecycleOperationsContract:
    schema_version: int
    contract_id: str
    states: tuple[LifecycleStateDefinition, ...]
    intake_aliases: tuple[tuple[str, str], ...]
    transitions: tuple[tuple[str, tuple[str, ...]], ...]
    required_project_fields: tuple[str, ...]
    required_issue_sections: tuple[str, ...]
    requires_dependencies_understood: bool
    transition_requirements: tuple[tuple[str, tuple[str, ...]], ...]
    execution_owner_field: str
    auto_expiry: bool
    delivery: tuple[tuple[str, Any], ...]
    terminal_state: str
    require_no_active_claim_after_close: bool
    guards: tuple[LifecycleGuard, ...]
    operations: tuple[LifecycleOperation, ...]
    verification_domains: tuple[tuple[str, str, str], ...]
    fingerprint: str

    @property
    def project_states(self) -> tuple[str, ...]:
        return tuple(item.token for item in self.states if item.project_status)

    @property
    def all_states(self) -> tuple[str, ...]:
        return tuple(item.token for item in self.states)

    @property
    def delivery_stages(self) -> tuple[str, ...]:
        return tuple(dict(self.delivery)["stages"])

    def transition_targets(self, state: str) -> tuple[str, ...]:
        return dict(self.transitions).get(state, ())

    def required_fields_for_transition(self, state: str) -> tuple[str, ...]:
        return dict(self.transition_requirements).get(state, ())

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "contract_id": self.contract_id,
            "states": [
                {"token": item.token, "label": item.label, "definition": item.definition, "project_status": item.project_status}
                for item in self.states
            ],
            "intake_aliases": dict(self.intake_aliases),
            "transitions": {name: list(targets) for name, targets in self.transitions},
            "readiness": {
                "required_project_fields": list(self.required_project_fields),
                "required_issue_sections": list(self.required_issue_sections),
                "requires_dependencies_understood": self.requires_dependencies_understood,
            },
            "transition_requirements": {name: list(fields) for name, fields in self.transition_requirements},
            "claim": {"execution_owner_field": self.execution_owner_field, "auto_expiry": self.auto_expiry},
            "delivery": dict(self.delivery),
            "completion": {
                "terminal_state": self.terminal_state,
                "require_no_active_claim_after_close": self.require_no_active_claim_after_close,
            },
            "guards": [
                {
                    "id": item.rule_id, "target": item.target, "condition": item.condition,
                    "reason_code": item.reason_code, "definition": item.definition,
                    "disposition": item.disposition,
                }
                for item in self.guards
            ],
            "operations": [
                {
                    "id": item.operation_id, "effect": item.effect,
                    "implementation_surface": item.implementation_surface,
                    "definition": item.definition,
                }
                for item in self.operations
            ],
            "verification_domains": [
                {"id": item[0], "field": item[1], "definition": item[2]}
                for item in self.verification_domains
            ],
        }


@dataclass(frozen=True, slots=True)
class SelectionRule:
    rule_id: str
    kind: str
    reason_code: str | None
    definition: str


@dataclass(frozen=True, slots=True)
class SelectionProfile:
    profile_id: str
    rules: tuple[str, ...]
    reason_overrides: tuple[tuple[str, str], ...]

    def reason(self, kind: str) -> str | None:
        return dict(self.reason_overrides).get(kind)


@dataclass(frozen=True, slots=True)
class WorkSelectionContract:
    schema_version: int
    contract_id: str
    fields: tuple[tuple[str, str], ...]
    eligible_states: tuple[str, ...]
    priority_order: tuple[str, ...]
    effort_order: tuple[str, ...]
    selection_tiers: tuple[str, ...]
    material_finding_severity: tuple[str, ...]
    operator_origin: str
    ranking: tuple[str, ...]
    dependency_evidence: tuple[str, ...]
    rules: tuple[SelectionRule, ...]
    profiles: tuple[SelectionProfile, ...]
    fingerprint: str

    def rule(self, kind: str) -> SelectionRule:
        for item in self.rules:
            if item.kind == kind:
                return item
        raise KeyError(kind)

    def profile(self, profile_id: str) -> SelectionProfile:
        for item in self.profiles:
            if item.profile_id == profile_id:
                return item
        raise KeyError(profile_id)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "contract_id": self.contract_id,
            "fields": dict(self.fields),
            "eligible_states": list(self.eligible_states),
            "priority_order": list(self.priority_order),
            "effort_order": list(self.effort_order),
            "selection_tiers": list(self.selection_tiers),
            "material_finding_severity": list(self.material_finding_severity),
            "operator_origin": self.operator_origin,
            "ranking": list(self.ranking),
            "dependency_evidence": list(self.dependency_evidence),
            "rules": [
                {
                    "id": item.rule_id,
                    "kind": item.kind,
                    "reason_code": item.reason_code,
                    "definition": item.definition,
                }
                for item in self.rules
            ],
            "profiles": {
                item.profile_id: {
                    "rules": list(item.rules),
                    "reason_overrides": dict(item.reason_overrides),
                }
                for item in self.profiles
            },
        }


@dataclass(frozen=True, slots=True)
class CanonicalWorkContracts:
    work_item: WorkItemSemanticsContract
    lifecycle: WorkLifecycleOperationsContract
    selection: WorkSelectionContract

    @property
    def fingerprints(self) -> dict[str, str]:
        return {
            "work_item_semantics": self.work_item.fingerprint,
            "work_lifecycle_operations": self.lifecycle.fingerprint,
            "work_selection": self.selection.fingerprint,
        }

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "work_item_semantics": self.work_item.to_json_dict(),
            "work_lifecycle_operations": self.lifecycle.to_json_dict(),
            "work_selection": self.selection.to_json_dict(),
            "fingerprints": self.fingerprints,
        }


def _parse_item(document: dict[str, Any]) -> WorkItemSemanticsContract:
    _exact_keys(document, _ITEM_KEYS, "work item semantics")
    if document["schema_version"] != 1 or document["contract_id"] != "work-item-semantics":
        raise ValueError("work item semantics identity is invalid")

    contexts: list[ApplicabilityContext] = []
    for raw in _array(document["contexts"], "contexts"):
        item = _object(raw, "context")
        _exact_keys(item, _CONTEXT_KEYS, "context")
        values = _unique(tuple(_text(value, "context value") for value in _array(item["values"], "context values")), "context values")
        contexts.append(ApplicabilityContext(_text(item["id"], "context id"), _text(item["definition"], "context definition"), _text(item["kind"], "context kind"), values))
    context_ids = _unique(tuple(item.context_id for item in contexts), "context ids")

    vocabularies: list[VocabularyDefinition] = []
    for raw in _array(document["vocabularies"], "vocabularies"):
        item = _object(raw, "vocabulary")
        _exact_keys(item, _VOCABULARY_KEYS, "vocabulary")
        values: list[VocabularyValue] = []
        for raw_value in _array(item["values"], "vocabulary values"):
            value = _object(raw_value, "vocabulary value")
            _exact_keys(value, _VALUE_KEYS, "vocabulary value")
            values.append(VocabularyValue(_text(value["token"], "vocabulary token"), _text(value["label"], "vocabulary label"), _text(value["definition"], "vocabulary definition")))
        _unique(tuple(value.token for value in values), "vocabulary tokens")
        vocabularies.append(VocabularyDefinition(_text(item["id"], "vocabulary id"), _text(item["definition"], "vocabulary definition"), tuple(values)))
    vocabulary_ids = _unique(tuple(item.vocabulary_id for item in vocabularies), "vocabulary ids")

    fields: list[CanonicalField] = []
    allowed_types = {"single_select", "text", "number", "date", "iteration", "repository", "native_datetime"}
    allowed_authorities = {"work_management", "work_management_then_repository_change", "repository_change", "git", "github", "actions", "derived"}
    allowed_directions = {"command", "evidence", "handoff"}
    for raw in _array(document["fields"], "fields"):
        item = _object(raw, "field")
        _exact_keys(item, _FIELD_KEYS, "field")
        provider_type = _text(item["provider_type"], "provider type")
        if provider_type not in allowed_types:
            raise ValueError(f"unsupported canonical provider type: {provider_type}")
        authority = _text(item["authority"], "field authority")
        direction = _text(item["direction"], "field direction")
        if authority not in allowed_authorities or direction not in allowed_directions:
            raise ValueError("canonical field authority or direction is invalid")
        if not isinstance(item["managed"], bool):
            raise ValueError("field managed must be a boolean")
        vocabulary = item["vocabulary"]
        if vocabulary is not None:
            vocabulary = _text(vocabulary, "field vocabulary")
            if vocabulary not in vocabulary_ids:
                raise ValueError(f"field references unknown vocabulary: {vocabulary}")
        applicable = _unique(tuple(_text(value, "record type") for value in _array(item["applicable_record_types"], "applicable record types")), "applicable record types")
        required = _unique(tuple(_text(value, "required context") for value in _array(item["required_contexts"], "required contexts")), "required contexts")
        if not set(required) <= set(context_ids):
            raise ValueError("field references unknown applicability context")
        fields.append(CanonicalField(
            _text(item["id"], "field id"), _text(item["name"], "field name"), provider_type,
            item["managed"], authority, direction, _text(item["definition"], "field definition"), vocabulary,
            applicable, required, _text(item["population"], "field population"),
        ))
    _unique(tuple(item.field_id for item in fields), "field ids")
    _unique(tuple(item.name.casefold() for item in fields), "field names")
    return WorkItemSemanticsContract(
        schema_version=1,
        contract_id="work-item-semantics",
        contexts=tuple(contexts),
        fields=tuple(fields),
        vocabularies=tuple(vocabularies),
        fingerprint=_fingerprint(document),
    )


def _string_tuple(value: Any, label: str) -> tuple[str, ...]:
    return _unique(tuple(_text(item, label) for item in _array(value, label)), label)


def _parse_lifecycle(document: dict[str, Any]) -> WorkLifecycleOperationsContract:
    _exact_keys(document, _LIFECYCLE_KEYS, "work lifecycle operations")
    if document["schema_version"] != 1 or document["contract_id"] != "work-lifecycle-operations":
        raise ValueError("work lifecycle operations identity is invalid")
    states: list[LifecycleStateDefinition] = []
    for raw in _array(document["states"], "states"):
        item = _object(raw, "state")
        _exact_keys(item, frozenset({"token", "label", "definition", "project_status"}), "state")
        if not isinstance(item["project_status"], bool):
            raise ValueError("state project_status must be a boolean")
        states.append(LifecycleStateDefinition(_text(item["token"], "state token"), _text(item["label"], "state label"), _text(item["definition"], "state definition"), item["project_status"]))
    state_tokens = _unique(tuple(item.token for item in states), "state tokens")

    aliases_raw = _object(document["intake_aliases"], "intake aliases")
    aliases = tuple(sorted((_text(key, "intake alias"), _text(value, "intake target")) for key, value in aliases_raw.items()))
    if any(target not in state_tokens for _alias, target in aliases):
        raise ValueError("intake alias references unknown lifecycle state")

    transitions_raw = _object(document["transitions"], "transitions")
    if set(transitions_raw) != set(state_tokens):
        raise ValueError("transitions must define every lifecycle state exactly once")
    transitions: list[tuple[str, tuple[str, ...]]] = []
    for source, raw_targets in transitions_raw.items():
        targets = _string_tuple(raw_targets, f"transitions.{source}")
        if not set(targets) <= set(state_tokens):
            raise ValueError("transition references unknown lifecycle state")
        transitions.append((source, targets))

    readiness = _object(document["readiness"], "readiness")
    _exact_keys(readiness, frozenset({"required_project_fields", "required_issue_sections", "requires_dependencies_understood"}), "readiness")
    if not isinstance(readiness["requires_dependencies_understood"], bool):
        raise ValueError("requires_dependencies_understood must be a boolean")

    requirements_raw = _object(document["transition_requirements"], "transition requirements")
    requirements = tuple(sorted((state, _string_tuple(fields, f"transition requirements.{state}")) for state, fields in requirements_raw.items()))
    if any(state not in state_tokens for state, _fields in requirements):
        raise ValueError("transition requirement references unknown lifecycle state")

    claim = _object(document["claim"], "claim")
    _exact_keys(claim, frozenset({"execution_owner_field", "auto_expiry"}), "claim")
    if not isinstance(claim["auto_expiry"], bool):
        raise ValueError("claim auto_expiry must be a boolean")

    delivery = _object(document["delivery"], "delivery")
    delivery_keys = frozenset({"stages", "stage_field", "change_id_field", "complexity_field", "risk_triggers_field", "change_created_stage", "complete_stage"})
    _exact_keys(delivery, delivery_keys, "delivery")
    stages = _string_tuple(delivery["stages"], "delivery stages")
    for key in delivery_keys - {"stages"}:
        _text(delivery[key], f"delivery.{key}")
    if delivery["change_created_stage"] not in stages or delivery["complete_stage"] not in stages:
        raise ValueError("delivery stage references must exist in stages")

    completion = _object(document["completion"], "completion")
    _exact_keys(completion, frozenset({"terminal_state", "require_no_active_claim_after_close"}), "completion")
    terminal_state = _text(completion["terminal_state"], "terminal state")
    if terminal_state not in state_tokens:
        raise ValueError("completion terminal_state is not canonical")
    if not isinstance(completion["require_no_active_claim_after_close"], bool):
        raise ValueError("completion claim flag must be a boolean")

    guards: list[LifecycleGuard] = []
    guard_keys = frozenset({"id", "target", "condition", "reason_code", "definition", "disposition"})
    for raw in _array(document["guards"], "guards"):
        item = _object(raw, "guard")
        _exact_keys(item, guard_keys, "guard")
        target = _text(item["target"], "guard target")
        if target not in state_tokens:
            raise ValueError("guard target is not canonical")
        disposition = _text(item["disposition"], "guard disposition")
        if disposition not in {"reject", "allow_with_reason"}:
            raise ValueError("guard disposition must be reject or allow_with_reason")
        guards.append(LifecycleGuard(
            _text(item["id"], "guard id"), target,
            _text(item["condition"], "guard condition"),
            _text(item["reason_code"], "guard reason"),
            _text(item["definition"], "guard definition"), disposition,
        ))
    _unique(tuple(item.rule_id for item in guards), "guard ids")

    operations: list[LifecycleOperation] = []
    operation_keys = frozenset({"id", "effect", "implementation_surface", "definition"})
    for raw in _array(document["operations"], "operations"):
        item = _object(raw, "operation")
        _exact_keys(item, operation_keys, "operation")
        operations.append(LifecycleOperation(
            _text(item["id"], "operation id"), _text(item["effect"], "operation effect"),
            _text(item["implementation_surface"], "implementation surface"), _text(item["definition"], "operation definition"),
        ))
    _unique(tuple(item.operation_id for item in operations), "operation ids")

    domains: list[tuple[str, str, str]] = []
    for raw in _array(document["verification_domains"], "verification domains"):
        item = _object(raw, "verification domain")
        _exact_keys(item, frozenset({"id", "field", "definition"}), "verification domain")
        domains.append((_text(item["id"], "verification domain id"), _text(item["field"], "verification domain field"), _text(item["definition"], "verification domain definition")))
    _unique(tuple(item[0] for item in domains), "verification domain ids")

    normalized_delivery = tuple((key, tuple(value) if key == "stages" else value) for key, value in delivery.items())
    return WorkLifecycleOperationsContract(
        1, "work-lifecycle-operations", tuple(states), aliases, tuple(sorted(transitions)),
        _string_tuple(readiness["required_project_fields"], "required project fields"),
        _string_tuple(readiness["required_issue_sections"], "required issue sections"),
        readiness["requires_dependencies_understood"], requirements,
        _text(claim["execution_owner_field"], "execution owner field"), claim["auto_expiry"],
        normalized_delivery, terminal_state, completion["require_no_active_claim_after_close"],
        tuple(guards), tuple(operations), tuple(domains), _fingerprint(document),
    )


def _parse_selection(document: dict[str, Any]) -> WorkSelectionContract:
    _exact_keys(document, _SELECTION_KEYS, "work selection")
    if document["schema_version"] != 1 or document["contract_id"] != "work-selection":
        raise ValueError("work selection identity is invalid")
    fields_raw = _object(document["fields"], "selection fields")
    expected_roles = {
        "state", "priority", "effort", "created", "blocked_by", "execution_owner",
        "record_type", "severity", "origin", "delivery_stage", "change_id",
    }
    if set(fields_raw) != expected_roles:
        raise ValueError("selection fields must declare the exact canonical roles")
    fields = tuple(sorted((role, _text(name, f"selection field {role}")) for role, name in fields_raw.items()))
    selection_tiers = _string_tuple(document["selection_tiers"], "selection tiers")
    if selection_tiers != ("defect", "material_finding", "unfinished", "new"):
        raise ValueError("selection tiers must be defect, material_finding, unfinished, new")
    material_finding_severity = _string_tuple(
        document["material_finding_severity"], "material finding severity"
    )
    operator_origin = _text(document["operator_origin"], "operator origin")
    ranking = _string_tuple(document["ranking"], "selection ranking")
    if any(item not in {"priority", "effort", "created_order", "record_id"} for item in ranking):
        raise ValueError("selection ranking contains unsupported values")
    rules: list[SelectionRule] = []
    rule_keys = frozenset({"id", "kind", "reason_code", "definition"})
    for raw in _array(document["rules"], "selection rules"):
        item = _object(raw, "selection rule")
        _exact_keys(item, rule_keys, "selection rule")
        reason = item["reason_code"]
        if reason is not None:
            reason = _text(reason, "selection reason code")
        rules.append(SelectionRule(
            _text(item["id"], "selection rule id"), _text(item["kind"], "selection rule kind"),
            reason, _text(item["definition"], "selection rule definition"),
        ))
    _unique(tuple(item.rule_id for item in rules), "selection rule ids")
    rule_kinds = _unique(tuple(item.kind for item in rules), "selection rule kinds")

    profiles_raw = _object(document["profiles"], "selection profiles")
    profiles: list[SelectionProfile] = []
    profile_keys = frozenset({"rules", "reason_overrides"})
    for profile_id, raw in profiles_raw.items():
        item = _object(raw, f"selection profile {profile_id}")
        _exact_keys(item, profile_keys, f"selection profile {profile_id}")
        profile_rules = _string_tuple(item["rules"], f"selection profile {profile_id} rules")
        if not set(profile_rules) <= set(rule_kinds):
            raise ValueError(f"selection profile {profile_id} references unknown rules")
        overrides_raw = _object(item["reason_overrides"], f"selection profile {profile_id} reason overrides")
        if not set(overrides_raw) <= set(profile_rules):
            raise ValueError(f"selection profile {profile_id} overrides an inactive rule")
        overrides = tuple(sorted(
            (_text(kind, "selection override kind"), _text(reason, "selection override reason"))
            for kind, reason in overrides_raw.items()
        ))
        profiles.append(SelectionProfile(
            _text(profile_id, "selection profile id"), profile_rules, overrides
        ))
    _unique(tuple(item.profile_id for item in profiles), "selection profile ids")
    return WorkSelectionContract(
        1, "work-selection", fields,
        _string_tuple(document["eligible_states"], "eligible states"),
        _string_tuple(document["priority_order"], "priority order"),
        _string_tuple(document["effort_order"], "effort order"), selection_tiers,
        material_finding_severity, operator_origin, ranking,
        _string_tuple(document["dependency_evidence"], "dependency evidence"),
        tuple(rules), tuple(profiles), _fingerprint(document),
    )


def _validate_cross_contracts(contracts: CanonicalWorkContracts) -> None:
    item = contracts.work_item
    lifecycle = contracts.lifecycle
    selection = contracts.selection
    field_names = {field.name for field in item.fields}
    for _role, field_name in selection.fields:
        if field_name not in field_names:
            raise ValueError(f"selection references unknown canonical field: {field_name}")
    for field_name in lifecycle.required_project_fields:
        if field_name not in field_names:
            raise ValueError(f"readiness references unknown canonical field: {field_name}")
    for _state, fields in lifecycle.transition_requirements:
        unknown = set(fields) - field_names
        if unknown:
            raise ValueError(f"transition requirements reference unknown canonical field: {min(unknown)}")
    for _domain, field_name, _definition in lifecycle.verification_domains:
        if field_name not in field_names:
            raise ValueError(f"verification domain references unknown canonical field: {field_name}")

    if lifecycle.project_states != item.vocabulary_tokens("status"):
        raise ValueError("lifecycle project states must exactly match canonical Status vocabulary")
    if tuple(selection.priority_order) != item.vocabulary_tokens("priority"):
        raise ValueError("selection priority order must exactly match canonical Priority vocabulary")
    if tuple(selection.effort_order) != item.vocabulary_tokens("effort"):
        raise ValueError("selection effort order must exactly match canonical Effort vocabulary")
    severity_tokens = set(item.vocabulary_tokens("severity"))
    if not selection.material_finding_severity or any(
        value not in severity_tokens for value in selection.material_finding_severity
    ):
        raise ValueError("material finding severity must use canonical Severity tokens")
    if selection.operator_origin not in item.vocabulary_tokens("origin"):
        raise ValueError("operator origin must be a canonical Origin token")
    if lifecycle.delivery_stages != item.vocabulary_tokens("delivery_stage"):
        raise ValueError("delivery stages must exactly match canonical Delivery Stage vocabulary")


def _default_contracts_path() -> Path:
    return Path(__file__).resolve().parents[3] / "settings" / "work-management" / "contracts"


def load_canonical_work_contracts(path: Path | None = None) -> CanonicalWorkContracts:
    root = path or _default_contracts_path()
    item_document = _object(json.loads((root / "work-item-semantics.json").read_text(encoding="utf-8")), "work item semantics")
    lifecycle_document = _object(json.loads((root / "work-lifecycle-operations.json").read_text(encoding="utf-8")), "work lifecycle operations")
    selection_document = _object(json.loads((root / "work-selection.json").read_text(encoding="utf-8")), "work selection")
    contracts = CanonicalWorkContracts(_parse_item(item_document), _parse_lifecycle(lifecycle_document), _parse_selection(selection_document))
    _validate_cross_contracts(contracts)
    return contracts


def validate_runtime_vocabulary(contracts: CanonicalWorkContracts) -> None:
    from .contracts import (
        ChangeComplexity,
        DeliveryStage,
        DocumentationImpact,
        Effort,
        LifecycleState,
        Priority,
        RecordType,
    )

    checks = (
        ("RecordType", tuple(item.value for item in RecordType), contracts.work_item.vocabulary_tokens("record_type")),
        ("Priority", tuple(item.value for item in Priority), contracts.work_item.vocabulary_tokens("priority")),
        ("Effort", tuple(item.value for item in Effort), contracts.work_item.vocabulary_tokens("effort")),
        ("DeliveryStage", tuple(item.value for item in DeliveryStage), contracts.work_item.vocabulary_tokens("delivery_stage")),
        ("ChangeComplexity", tuple(item.value for item in ChangeComplexity), contracts.work_item.vocabulary_tokens("complexity")),
        ("DocumentationImpact", tuple(item.value for item in DocumentationImpact), contracts.work_item.vocabulary_tokens("documentation_impact")),
    )
    for label, observed, expected in checks:
        if observed != expected:
            raise ValueError(f"{label} values drift from canonical Work vocabulary")
    if {item.value for item in LifecycleState} != set(contracts.lifecycle.all_states):
        raise ValueError("LifecycleState values drift from canonical Work lifecycle")


__all__ = [
    "ApplicabilityContext", "CanonicalField", "CanonicalWorkContracts",
    "LifecycleGuard", "LifecycleOperation", "LifecycleStateDefinition",
    "SelectionProfile", "SelectionRule", "VocabularyDefinition", "VocabularyValue",
    "WorkItemSemanticsContract", "WorkLifecycleOperationsContract", "WorkSelectionContract",
    "load_canonical_work_contracts", "validate_command_plane_projection",
    "validate_runtime_vocabulary",
]


def _projection_match(observed: Any, expected: Any, label: str) -> None:
    if observed != expected:
        raise ValueError(f"{label} drifts from canonical Work contract")


def validate_command_plane_projection(
    document: Mapping[str, Any], contracts: CanonicalWorkContracts
) -> None:
    item = contracts.work_item
    lifecycle = contracts.lifecycle
    selection = contracts.selection
    expected_authority = {
        field.name: {"authority": field.authority, "direction": field.direction}
        for field in item.fields
    }
    _projection_match(document.get("field_authority"), expected_authority, "field_authority")
    _projection_match(document.get("work_states"), list(lifecycle.project_states), "work_states")
    if "intake_aliases" in document:
        _projection_match(document["intake_aliases"], dict(lifecycle.intake_aliases), "intake_aliases")
    expected_transitions = {source: list(targets) for source, targets in lifecycle.transitions}
    _projection_match(document.get("transitions"), expected_transitions, "transitions")

    fields = dict(selection.fields)
    expected_queue = {
        "state_field": fields["state"],
        "priority_field": fields["priority"],
        "effort_field": fields["effort"],
        "created_field": fields["created"],
        "blocked_by_field": fields["blocked_by"],
        "eligible_states": list(selection.eligible_states),
        "priority_order": list(selection.priority_order),
        "effort_order": list(selection.effort_order),
        "ranking": list(selection.ranking),
    }
    observed_queue = _object(document.get("queue"), "queue")
    for key, expected in expected_queue.items():
        _projection_match(observed_queue.get(key), expected, f"queue.{key}")
    _projection_match(
        document.get("readiness"),
        {
            "required_project_fields": list(lifecycle.required_project_fields),
            "required_issue_sections": list(lifecycle.required_issue_sections),
            "requires_dependencies_understood": lifecycle.requires_dependencies_understood,
        },
        "readiness",
    )
    _projection_match(
        document.get("transition_requirements"),
        {state: list(fields) for state, fields in lifecycle.transition_requirements},
        "transition_requirements",
    )
    _projection_match(
        document.get("claim"),
        {"execution_owner_field": lifecycle.execution_owner_field, "auto_expiry": lifecycle.auto_expiry},
        "claim",
    )
    delivery = dict(lifecycle.delivery)
    delivery["stages"] = list(delivery["stages"])
    _projection_match(document.get("delivery_stages"), delivery.pop("stages"), "delivery_stages")
    _projection_match(document.get("delivery"), delivery, "delivery")
    _projection_match(
        document.get("completion"),
        {
            "terminal_state": lifecycle.terminal_state,
            "require_no_active_claim_after_close": lifecycle.require_no_active_claim_after_close,
        },
        "completion",
    )
