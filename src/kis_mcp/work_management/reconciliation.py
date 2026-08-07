from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol, TypeAlias, runtime_checkable

JsonScalar: TypeAlias = str | int | float | bool | None
_PROJECT_ID = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
_RECORD_ID = re.compile(r"^[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-[0-9]+$")


class ReconciliationAction(StrEnum):
    CREATE = "create"
    UPDATE = "update"
    NOOP = "noop"
    ORPHANED = "orphaned"
    CONFLICT = "conflict"
    UNSUPPORTED = "unsupported"
    INACCESSIBLE = "inaccessible"


def _required_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _project_id(value: Any) -> str:
    normalized = _required_text(value, "project_id")
    if _PROJECT_ID.fullmatch(normalized) is None:
        raise ValueError("project_id must use lower-case kebab-case")
    return normalized


def _record_id(value: Any) -> str:
    normalized = _required_text(value, "record_id")
    if _RECORD_ID.fullmatch(normalized) is None:
        raise ValueError("record_id must use an upper-case stable prefix and number")
    return normalized


def _fields(value: tuple[tuple[str, JsonScalar], ...]) -> tuple[tuple[str, JsonScalar], ...]:
    normalized: list[tuple[str, JsonScalar]] = []
    for name, field_value in value:
        field_name = _required_text(name, "field name")
        if field_value is not None and not isinstance(field_value, (str, int, float, bool)):
            raise ValueError("field values must be JSON scalars")
        normalized.append((field_name, field_value))
    names = [name.casefold() for name, _ in normalized]
    if len(set(names)) != len(names):
        raise ValueError("field names must be unique")
    return tuple(sorted(normalized, key=lambda item: item[0].casefold()))


@dataclass(frozen=True, slots=True)
class DesiredProjection:
    project_id: str
    record_id: str
    fields: tuple[tuple[str, JsonScalar], ...]
    expected_revision: str | None = None
    source_repository: str | None = None
    source_number: int | None = None
    source_kind: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_id", _project_id(self.project_id))
        object.__setattr__(self, "record_id", _record_id(self.record_id))
        object.__setattr__(self, "fields", _fields(self.fields))
        if self.expected_revision is not None:
            object.__setattr__(
                self,
                "expected_revision",
                _required_text(self.expected_revision, "expected_revision"),
            )
        if self.source_repository is not None:
            repository = _required_text(self.source_repository, "source_repository")
            if repository.count("/") != 1 or any(character.isspace() for character in repository):
                raise ValueError("source_repository must use owner/repository")
            object.__setattr__(self, "source_repository", repository)
        if self.source_number is not None:
            if isinstance(self.source_number, bool) or not isinstance(self.source_number, int) or self.source_number <= 0:
                raise ValueError("source_number must be a positive integer")
        if self.source_kind is not None:
            kind = _required_text(self.source_kind, "source_kind").casefold()
            if kind not in {"issue", "pull_request"}:
                raise ValueError("source_kind must be issue or pull_request")
            object.__setattr__(self, "source_kind", kind)
        supplied = (
            self.source_repository is not None,
            self.source_number is not None,
            self.source_kind is not None,
        )
        if any(supplied) and not all(supplied):
            raise ValueError("source identity requires repository, number, and kind")


@dataclass(frozen=True, slots=True)
class ObservedProjection:
    project_id: str
    record_id: str
    fields: tuple[tuple[str, JsonScalar], ...]
    revision: str | None
    accessible: bool = True
    external_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_id", _project_id(self.project_id))
        object.__setattr__(self, "record_id", _record_id(self.record_id))
        object.__setattr__(self, "fields", _fields(self.fields))
        if self.revision is not None:
            object.__setattr__(self, "revision", _required_text(self.revision, "revision"))
        if not isinstance(self.accessible, bool):
            raise ValueError("accessible must be a boolean")
        if self.external_id is not None:
            object.__setattr__(
                self,
                "external_id",
                _required_text(self.external_id, "external_id"),
            )


@dataclass(frozen=True, slots=True)
class ReconciliationDecision:
    project_id: str
    record_id: str
    action: ReconciliationAction
    changed_fields: tuple[str, ...] = ()
    desired_fields: tuple[tuple[str, JsonScalar], ...] = ()
    external_id: str | None = None
    source_repository: str | None = None
    source_number: int | None = None
    source_kind: str | None = None
    observed_revision: str | None = None
    reason: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_id", _project_id(self.project_id))
        object.__setattr__(self, "record_id", _record_id(self.record_id))
        if not isinstance(self.action, ReconciliationAction):
            raise ValueError("action must be ReconciliationAction")
        object.__setattr__(
            self,
            "changed_fields",
            tuple(sorted(_required_text(item, "changed field") for item in self.changed_fields)),
        )
        object.__setattr__(self, "desired_fields", _fields(self.desired_fields))
        if self.external_id is not None:
            object.__setattr__(self, "external_id", _required_text(self.external_id, "external_id"))
        source = DesiredProjection(
            project_id=self.project_id,
            record_id=self.record_id,
            fields=self.desired_fields,
            source_repository=self.source_repository,
            source_number=self.source_number,
            source_kind=self.source_kind,
        )
        object.__setattr__(self, "source_repository", source.source_repository)
        object.__setattr__(self, "source_number", source.source_number)
        object.__setattr__(self, "source_kind", source.source_kind)
        if self.observed_revision is not None:
            object.__setattr__(
                self,
                "observed_revision",
                _required_text(self.observed_revision, "observed_revision"),
            )
        object.__setattr__(self, "reason", _required_text(self.reason, "reason"))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "record_id": self.record_id,
            "action": self.action.value,
            "changed_fields": list(self.changed_fields),
            "desired_fields": dict(self.desired_fields),
            "external_id": self.external_id,
            "source_repository": self.source_repository,
            "source_number": self.source_number,
            "source_kind": self.source_kind,
            "observed_revision": self.observed_revision,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class ReconciliationOutcome:
    project_id: str
    record_id: str
    action: ReconciliationAction
    applied: bool
    success: bool
    provider_revision: str | None = None
    message: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_id", _project_id(self.project_id))
        object.__setattr__(self, "record_id", _record_id(self.record_id))
        if not isinstance(self.action, ReconciliationAction):
            raise ValueError("action must be ReconciliationAction")
        if not isinstance(self.applied, bool) or not isinstance(self.success, bool):
            raise ValueError("outcome flags must be booleans")
        if self.provider_revision is not None:
            object.__setattr__(
                self,
                "provider_revision",
                _required_text(self.provider_revision, "provider_revision"),
            )
        if self.message is not None:
            object.__setattr__(self, "message", _required_text(self.message, "message"))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "record_id": self.record_id,
            "action": self.action.value,
            "applied": self.applied,
            "success": self.success,
            "provider_revision": self.provider_revision,
            "message": self.message,
        }


@runtime_checkable
class ReconciliationBackend(Protocol):
    async def apply_reconciliation(
        self,
        decision: ReconciliationDecision,
        *,
        idempotency_key: str,
    ) -> ReconciliationOutcome: ...


def plan_reconciliation(
    desired: tuple[DesiredProjection, ...],
    observed: tuple[ObservedProjection, ...],
    *,
    supported_fields: tuple[str, ...] = (),
) -> tuple[ReconciliationDecision, ...]:
    desired_map: dict[tuple[str, str], DesiredProjection] = {}
    for item in desired:
        key = (item.project_id, item.record_id)
        if key in desired_map:
            raise ValueError(f"duplicate desired projection: {item.project_id}/{item.record_id}")
        desired_map[key] = item
    observed_map: dict[tuple[str, str], ObservedProjection] = {}
    for item in observed:
        key = (item.project_id, item.record_id)
        if key in observed_map:
            raise ValueError(f"duplicate observed projection: {item.project_id}/{item.record_id}")
        observed_map[key] = item
    supported = set(supported_fields)
    decisions: list[ReconciliationDecision] = []
    for key in sorted(desired_map):
        expected = desired_map[key]
        actual = observed_map.get(key)
        desired_fields = dict(expected.fields)
        unsupported = tuple(sorted(set(desired_fields) - supported)) if supported else ()
        if unsupported:
            decisions.append(
                ReconciliationDecision(
                    project_id=expected.project_id,
                    record_id=expected.record_id,
                    action=ReconciliationAction.UNSUPPORTED,
                    changed_fields=unsupported,
                    desired_fields=expected.fields,
                    external_id=actual.external_id if actual else None,
                    source_repository=expected.source_repository,
                    source_number=expected.source_number,
                    source_kind=expected.source_kind,
                    observed_revision=actual.revision if actual else None,
                    reason="desired fields are not supported by the backend",
                )
            )
            continue
        if actual is not None and not actual.accessible:
            decisions.append(
                ReconciliationDecision(
                    project_id=expected.project_id,
                    record_id=expected.record_id,
                    action=ReconciliationAction.INACCESSIBLE,
                    desired_fields=expected.fields,
                    external_id=actual.external_id if actual else None,
                    source_repository=expected.source_repository,
                    source_number=expected.source_number,
                    source_kind=expected.source_kind,
                    observed_revision=actual.revision,
                    reason="observed record is inaccessible",
                )
            )
            continue
        if actual is None:
            decisions.append(
                ReconciliationDecision(
                    project_id=expected.project_id,
                    record_id=expected.record_id,
                    action=ReconciliationAction.CREATE,
                    changed_fields=tuple(desired_fields),
                    desired_fields=expected.fields,
                    external_id=actual.external_id if actual else None,
                    source_repository=expected.source_repository,
                    source_number=expected.source_number,
                    source_kind=expected.source_kind,
                    reason="record is absent from observed state",
                )
            )
            continue
        observed_fields = dict(actual.fields)
        changed = tuple(
            sorted(
                name
                for name, value in desired_fields.items()
                if observed_fields.get(name) != value
            )
        )
        if not changed:
            decisions.append(
                ReconciliationDecision(
                    project_id=expected.project_id,
                    record_id=expected.record_id,
                    action=ReconciliationAction.NOOP,
                    desired_fields=expected.fields,
                    external_id=actual.external_id if actual else None,
                    source_repository=expected.source_repository,
                    source_number=expected.source_number,
                    source_kind=expected.source_kind,
                    observed_revision=actual.revision,
                    reason="desired and observed fields already match",
                )
            )
            continue
        if (
            expected.expected_revision is not None
            and expected.expected_revision != actual.revision
        ):
            decisions.append(
                ReconciliationDecision(
                    project_id=expected.project_id,
                    record_id=expected.record_id,
                    action=ReconciliationAction.CONFLICT,
                    changed_fields=changed,
                    desired_fields=expected.fields,
                    external_id=actual.external_id if actual else None,
                    source_repository=expected.source_repository,
                    source_number=expected.source_number,
                    source_kind=expected.source_kind,
                    observed_revision=actual.revision,
                    reason="observed revision does not match expected revision",
                )
            )
            continue
        decisions.append(
            ReconciliationDecision(
                project_id=expected.project_id,
                record_id=expected.record_id,
                action=ReconciliationAction.UPDATE,
                changed_fields=changed,
                desired_fields=expected.fields,
                external_id=actual.external_id,
                source_repository=expected.source_repository,
                source_number=expected.source_number,
                source_kind=expected.source_kind,
                observed_revision=actual.revision,
                reason="observed fields differ from desired state",
            )
        )
    for key in sorted(set(observed_map) - set(desired_map)):
        actual = observed_map[key]
        decisions.append(
            ReconciliationDecision(
                project_id=actual.project_id,
                record_id=actual.record_id,
                action=ReconciliationAction.ORPHANED,
                changed_fields=tuple(name for name, _value in actual.fields),
                external_id=actual.external_id,
                observed_revision=actual.revision,
                reason="observed record is absent from desired state",
            )
        )
    return tuple(sorted(decisions, key=lambda item: (item.project_id, item.record_id)))


async def run_reconciliation(
    decisions: tuple[ReconciliationDecision, ...],
    backend: ReconciliationBackend,
    *,
    apply: bool = False,
    idempotency_key: str | None = None,
) -> tuple[ReconciliationOutcome, ...]:
    if apply:
        base_key = _required_text(idempotency_key, "idempotency_key")
    else:
        base_key = "preview"
    outcomes: list[ReconciliationOutcome] = []
    for decision in decisions:
        actionable = decision.action in {
            ReconciliationAction.CREATE,
            ReconciliationAction.UPDATE,
        }
        if apply and actionable:
            outcomes.append(
                await backend.apply_reconciliation(
                    decision,
                    idempotency_key=f"{base_key}:{decision.record_id}",
                )
            )
            continue
        success = decision.action not in {
            ReconciliationAction.ORPHANED,
            ReconciliationAction.CONFLICT,
            ReconciliationAction.UNSUPPORTED,
            ReconciliationAction.INACCESSIBLE,
        }
        outcomes.append(
            ReconciliationOutcome(
                project_id=decision.project_id,
                record_id=decision.record_id,
                action=decision.action,
                applied=False,
                success=success,
                provider_revision=decision.observed_revision,
                message=decision.reason,
            )
        )
    return tuple(outcomes)


__all__ = [
    "DesiredProjection",
    "ObservedProjection",
    "ReconciliationAction",
    "ReconciliationBackend",
    "ReconciliationDecision",
    "ReconciliationOutcome",
    "plan_reconciliation",
    "run_reconciliation",
]
