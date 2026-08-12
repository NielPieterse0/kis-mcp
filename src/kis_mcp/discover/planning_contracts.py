from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields
from enum import StrEnum
from typing import Any

from .contracts import Confidence, ProjectIdentity

PLAN_CHANGE_SCHEMA_VERSION = 1
PLAN_CHANGE_TOOL = "plan_change"


def _required(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _positive(value: int, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{label} must be a positive integer")
    return value


def _json(value: Any) -> Any:
    if hasattr(value, "to_json_dict"):
        return value.to_json_dict()
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _json(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json(item) for item in value]
    return value


class _Record:
    def to_json_dict(self) -> dict[str, Any]:
        return {field.name: _json(getattr(self, field.name)) for field in fields(self)}


@dataclass(frozen=True, slots=True)
class PlanChangeRequest(_Record):
    project: str
    task: str
    source: str = "working_tree"
    commit_ref: str | None = None
    base_ref: str | None = None
    head_ref: str | None = None
    max_chars: int = 20_000
    max_files: int = 12
    max_symbols: int = 50
    max_relationships: int = 50
    max_dependants: int = 100
    max_tests: int = 100
    max_verifications: int = 50

    def __post_init__(self) -> None:
        _required(self.project, "plan change project")
        _required(self.task, "plan change task")
        source = _required(self.source, "plan change source").casefold()
        if source not in {"working_tree", "staged", "commit", "range", "branch"}:
            raise ValueError("plan change source is unsupported")
        object.__setattr__(self, "source", source)
        for name in (
            "max_chars",
            "max_files",
            "max_symbols",
            "max_relationships",
            "max_dependants",
            "max_tests",
            "max_verifications",
        ):
            _positive(getattr(self, name), f"plan change {name}")


@dataclass(frozen=True, slots=True)
class PlanChangeUnknown(_Record):
    code: str
    reason: str

    def __post_init__(self) -> None:
        _required(self.code, "plan change unknown code")
        _required(self.reason, "plan change unknown reason")


@dataclass(frozen=True, slots=True)
class PlanChangeAuthority(_Record):
    instructions: tuple[str, ...]
    documentation: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PlanChangePattern(_Record):
    classification: str
    path: str | None
    reason: str
    confidence: Confidence

    def __post_init__(self) -> None:
        if self.classification not in {"REUSE", "EXTEND", "REPLACE", "NEW"}:
            raise ValueError("plan change pattern classification is unsupported")
        if self.path is not None:
            _required(self.path, "plan change pattern path")
        _required(self.reason, "plan change pattern reason")


@dataclass(frozen=True, slots=True)
class PlanChangeSummary(_Record):
    source: str
    changed_paths: tuple[str, ...]
    planned_paths: tuple[str, ...]
    planned_impact_fingerprint: str

    def __post_init__(self) -> None:
        if len(self.planned_impact_fingerprint) != 64 or any(
            char not in "0123456789abcdef" for char in self.planned_impact_fingerprint
        ):
            raise ValueError("planned impact fingerprint must be 64 lowercase hexadecimal characters")


@dataclass(frozen=True, slots=True)
class PlanChangeAffected(_Record):
    context_files: tuple[str, ...]
    modules: tuple[str, ...]
    symbols: tuple[str, ...]
    tests: tuple[str, ...]
    contracts: tuple[str, ...]
    documentation: tuple[str, ...]
    configuration: tuple[str, ...]
    policy: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PlanChangeVerification(_Record):
    ids: tuple[str, ...]
    handoffs: tuple[Mapping[str, Any], ...]


@dataclass(frozen=True, slots=True)
class ActiveChangeClaim(_Record):
    change_id: str
    status: str
    owned_paths: tuple[str, ...]
    shared_paths: tuple[str, ...] = ()
    branch: str | None = None


@dataclass(frozen=True, slots=True)
class ClaimConflict(_Record):
    change_id: str
    paths: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PlanChangeGovernance(_Record):
    active_claims: tuple[ActiveChangeClaim, ...]
    conflicts: tuple[ClaimConflict, ...]


@dataclass(frozen=True, slots=True)
class PlanChangeResponse:
    project: ProjectIdentity
    task: str
    authority: PlanChangeAuthority
    change: PlanChangeSummary
    affected: PlanChangeAffected
    verification: PlanChangeVerification
    implementation_steps: tuple[Mapping[str, Any], ...]
    patterns: tuple[PlanChangePattern, ...]
    governance: PlanChangeGovernance
    risks: tuple[str, ...]
    unknowns: tuple[PlanChangeUnknown, ...]
    confidence: Confidence
    truncated: bool
    truncation_reasons: tuple[str, ...]
    fingerprint: str
    execution_performed: bool = False
    schema_version: int = PLAN_CHANGE_SCHEMA_VERSION
    tool: str = PLAN_CHANGE_TOOL

    def __post_init__(self) -> None:
        if self.schema_version != PLAN_CHANGE_SCHEMA_VERSION or self.tool != PLAN_CHANGE_TOOL:
            raise ValueError("plan change response identity is fixed")
        if self.execution_performed:
            raise ValueError("Discover plan_change must never execute work")
        if self.truncated != bool(self.truncation_reasons):
            raise ValueError("plan change truncation state is inconsistent")
        if len(self.fingerprint) != 64 or any(c not in "0123456789abcdef" for c in self.fingerprint):
            raise ValueError("plan change fingerprint must be 64 lowercase hexadecimal characters")

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "tool": self.tool,
            "project": self.project.to_json_dict(),
            "task": self.task,
            "authority": self.authority.to_json_dict(),
            "change": self.change.to_json_dict(),
            "affected": self.affected.to_json_dict(),
            "verification": self.verification.to_json_dict(),
            "implementation_steps": _json(self.implementation_steps),
            "patterns": _json(self.patterns),
            "governance": self.governance.to_json_dict(),
            "risks": list(self.risks),
            "unknowns": [item.to_json_dict() for item in self.unknowns],
            "confidence": self.confidence.value,
            "truncated": self.truncated,
            "truncation_reasons": list(self.truncation_reasons),
            "fingerprint": self.fingerprint,
            "execution_performed": self.execution_performed,
        }


__all__ = [
    "ActiveChangeClaim",
    "ClaimConflict",
    "PlanChangeAffected",
    "PlanChangeAuthority",
    "PlanChangeGovernance",
    "PlanChangePattern",
    "PlanChangeRequest",
    "PlanChangeResponse",
    "PlanChangeSummary",
    "PlanChangeUnknown",
    "PlanChangeVerification",
]
