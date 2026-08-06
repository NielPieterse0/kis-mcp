from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, TypeAlias

from .contracts import PUBLIC_SCHEMA_VERSION, RecordType, WorkRecord


def _text(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _texts(values: tuple[str, ...], label: str, *, required: bool = False) -> tuple[str, ...]:
    normalized = tuple(_text(value, label) for value in values)
    if required and not normalized:
        raise ValueError(f"{label} must contain at least one value")
    if len({value.casefold() for value in normalized}) != len(normalized):
        raise ValueError(f"{label} must contain unique values")
    return normalized


class RecordDetails(Protocol):
    record_type: RecordType

    def to_json_dict(self) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class DecisionDetails:
    decision: str
    owner: str
    authority_paths: tuple[str, ...]
    alternatives: tuple[str, ...] = ()
    consequences: tuple[str, ...] = ()
    record_type: RecordType = field(default=RecordType.DECISION, init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "decision", _text(self.decision, "decision"))
        object.__setattr__(self, "owner", _text(self.owner, "owner"))
        object.__setattr__(self, "authority_paths", _texts(self.authority_paths, "authority_paths", required=True))
        object.__setattr__(self, "alternatives", _texts(self.alternatives, "alternatives"))
        object.__setattr__(self, "consequences", _texts(self.consequences, "consequences", required=True))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "record_type": self.record_type.value,
            "decision": self.decision,
            "owner": self.owner,
            "authority_paths": list(self.authority_paths),
            "alternatives": list(self.alternatives),
            "consequences": list(self.consequences),
        }


@dataclass(frozen=True, slots=True)
class AssumptionDetails:
    statement: str
    confidence: str
    validation_method: str
    review_trigger: str
    invalidation_condition: str
    record_type: RecordType = field(default=RecordType.ASSUMPTION, init=False)

    def __post_init__(self) -> None:
        for field in ("statement", "confidence", "validation_method", "review_trigger", "invalidation_condition"):
            object.__setattr__(self, field, _text(getattr(self, field), field))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "record_type": self.record_type.value,
            "statement": self.statement,
            "confidence": self.confidence,
            "validation_method": self.validation_method,
            "review_trigger": self.review_trigger,
            "invalidation_condition": self.invalidation_condition,
        }


@dataclass(frozen=True, slots=True)
class RiskDetails:
    statement: str
    likelihood: str
    consequence: str
    mitigation: str
    record_type: RecordType = field(default=RecordType.RISK, init=False)

    def __post_init__(self) -> None:
        for field in ("statement", "likelihood", "consequence", "mitigation"):
            object.__setattr__(self, field, _text(getattr(self, field), field))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "record_type": self.record_type.value,
            "statement": self.statement,
            "likelihood": self.likelihood,
            "consequence": self.consequence,
            "mitigation": self.mitigation,
        }


@dataclass(frozen=True, slots=True)
class ApprovalDetails:
    decision: str
    approver: str
    scope: str
    evidence: str | None = None
    record_type: RecordType = field(default=RecordType.APPROVAL, init=False)

    def __post_init__(self) -> None:
        for field in ("decision", "approver", "scope"):
            object.__setattr__(self, field, _text(getattr(self, field), field))
        if self.evidence is not None:
            object.__setattr__(self, "evidence", _text(self.evidence, "evidence"))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "record_type": self.record_type.value,
            "decision": self.decision,
            "approver": self.approver,
            "scope": self.scope,
            "evidence": self.evidence,
        }


@dataclass(frozen=True, slots=True)
class HoldDetails:
    reason: str
    owner: str
    protected_assets: tuple[str, ...]
    review_trigger: str
    resumption_conditions: str
    cancellation_conditions: str
    record_type: RecordType = field(default=RecordType.HOLD, init=False)

    def __post_init__(self) -> None:
        for field in ("reason", "owner", "review_trigger", "resumption_conditions", "cancellation_conditions"):
            object.__setattr__(self, field, _text(getattr(self, field), field))
        object.__setattr__(self, "protected_assets", _texts(self.protected_assets, "protected_assets", required=True))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "record_type": self.record_type.value,
            "reason": self.reason,
            "owner": self.owner,
            "protected_assets": list(self.protected_assets),
            "review_trigger": self.review_trigger,
            "resumption_conditions": self.resumption_conditions,
            "cancellation_conditions": self.cancellation_conditions,
        }


GovernanceDetails: TypeAlias = DecisionDetails | AssumptionDetails | RiskDetails | ApprovalDetails | HoldDetails


@dataclass(frozen=True, slots=True)
class GovernanceRecord:
    record: WorkRecord
    details: GovernanceDetails
    note: str | None = None
    schema_version: int = PUBLIC_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PUBLIC_SCHEMA_VERSION:
            raise ValueError("governance record schema_version must be 1")
        if not isinstance(self.record, WorkRecord):
            raise ValueError("record must be a WorkRecord")
        if self.record.record_type is not self.details.record_type:
            raise ValueError("record type and governance details must match")
        if self.note is not None:
            object.__setattr__(self, "note", _text(self.note, "note"))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "record": self.record.to_json_dict(),
            "details": self.details.to_json_dict(),
            "note": self.note,
        }


__all__ = [
    "ApprovalDetails",
    "AssumptionDetails",
    "DecisionDetails",
    "GovernanceDetails",
    "GovernanceRecord",
    "HoldDetails",
    "RecordDetails",
    "RiskDetails",
]
