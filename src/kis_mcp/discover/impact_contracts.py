from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields
from enum import StrEnum
from typing import Any

from .contracts import Confidence, ProjectIdentity

INSPECT_IMPACT_SCHEMA_VERSION = 1
INSPECT_IMPACT_TOOL = "inspect_impact"


def _required(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _positive(value: int, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{label} must be a positive integer")
    return value


def _non_negative(value: int, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def _path(value: str) -> str:
    normalized = _required(value, "impact changed path").replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    normalized = normalized.strip("/")
    if not normalized or normalized.startswith("../") or "/../" in normalized:
        raise ValueError("impact changed path must be repository-relative")
    return normalized


def _json(value: Any) -> Any:
    if hasattr(value, "to_json_dict"):
        return value.to_json_dict()
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _json(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise ValueError(f"value is not JSON-compatible: {type(value).__name__}")


class _Record:
    def to_json_dict(self) -> dict[str, Any]:
        return {field.name: _json(getattr(self, field.name)) for field in fields(self)}


@dataclass(frozen=True, slots=True)
class ImpactBudget(_Record):
    max_symbols: int
    max_dependants: int
    max_tests: int
    max_verifications: int

    def __post_init__(self) -> None:
        for name in ("max_symbols", "max_dependants", "max_tests", "max_verifications"):
            _positive(getattr(self, name), f"impact budget {name}")


@dataclass(frozen=True, slots=True)
class InspectImpactRequest(_Record):
    project: str
    changed_paths: tuple[str, ...]
    budget: ImpactBudget
    task_terms: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _required(self.project, "impact project")
        normalized = tuple(dict.fromkeys(_path(item) for item in self.changed_paths))
        if not normalized:
            raise ValueError("impact changed_paths must not be empty")
        if normalized != self.changed_paths:
            object.__setattr__(self, "changed_paths", normalized)
        if not isinstance(self.budget, ImpactBudget):
            raise ValueError("impact budget must be an ImpactBudget")
        normalized_terms = tuple(
            dict.fromkeys(
                item.strip().casefold()
                for item in self.task_terms
                if isinstance(item, str) and item.strip()
            )
        )
        if normalized_terms != self.task_terms:
            object.__setattr__(self, "task_terms", normalized_terms)

    def to_json_dict(self) -> dict[str, Any]:
        payload = _Record.to_json_dict(self)
        if not self.task_terms:
            payload.pop("task_terms")
        return payload


@dataclass(frozen=True, slots=True)
class ImpactSymbol(_Record):
    qualified_name: str
    module: str
    name: str
    kind: str
    path: str
    line: int
    provenance: str = "python_ast"

    def __post_init__(self) -> None:
        for value, label in (
            (self.qualified_name, "impact symbol qualified_name"),
            (self.module, "impact symbol module"),
            (self.name, "impact symbol name"),
            (self.kind, "impact symbol kind"),
            (self.path, "impact symbol path"),
            (self.provenance, "impact symbol provenance"),
        ):
            _required(value, label)
        _positive(self.line, "impact symbol line")


@dataclass(frozen=True, slots=True)
class ImpactDependant(_Record):
    kind: str
    source: str
    target: str
    path: str
    line: int
    confidence: Confidence
    provenance: str = "python_ast"

    def __post_init__(self) -> None:
        if self.kind not in {"import", "call", "inheritance"}:
            raise ValueError("impact dependant kind is unsupported")
        for value, label in (
            (self.source, "impact dependant source"),
            (self.target, "impact dependant target"),
            (self.path, "impact dependant path"),
            (self.provenance, "impact dependant provenance"),
        ):
            _required(value, label)
        _positive(self.line, "impact dependant line")


@dataclass(frozen=True, slots=True)
class ImpactTest(_Record):
    path: str
    reason: str
    confidence: Confidence
    matched_targets: tuple[str, ...]
    provenance: str

    def __post_init__(self) -> None:
        for value, label in (
            (self.path, "impact test path"),
            (self.reason, "impact test reason"),
            (self.provenance, "impact test provenance"),
        ):
            _required(value, label)
        if not self.matched_targets:
            raise ValueError("impact test matched_targets must not be empty")


@dataclass(frozen=True, slots=True)
class ImpactVerificationHandoff(_Record):
    handoff_id: str
    verification_id: str
    category: str
    reason: str
    profile: str
    arguments: tuple[str, ...]
    source_path: str
    target_plane: str = "work"
    workflow: str = "run_verification"
    execution_available: bool = False

    def __post_init__(self) -> None:
        for value, label in (
            (self.handoff_id, "impact handoff id"),
            (self.verification_id, "impact verification id"),
            (self.category, "impact verification category"),
            (self.reason, "impact verification reason"),
            (self.profile, "impact verification profile"),
            (self.source_path, "impact verification source_path"),
        ):
            _required(value, label)
        if self.target_plane != "work" or self.workflow != "run_verification":
            raise ValueError("impact handoff target is fixed")
        if self.execution_available:
            raise ValueError("Discover impact handoffs must not be executable")


@dataclass(frozen=True, slots=True)
class ImpactRelationship(_Record):
    kind: str
    source_path: str
    target_path: str
    reason: str
    confidence: Confidence
    provenance: str

    def __post_init__(self) -> None:
        if self.kind not in {
            "contract_reference",
            "configuration_reference",
            "documentation_reference",
            "policy_reference",
            "semantic_reference",
            "task_term",
        }:
            raise ValueError("impact relationship kind is unsupported")
        for value, label in (
            (self.source_path, "impact relationship source_path"),
            (self.target_path, "impact relationship target_path"),
            (self.reason, "impact relationship reason"),
            (self.provenance, "impact relationship provenance"),
        ):
            _required(value, label)


@dataclass(frozen=True, slots=True)
class ImpactImplementationStep(_Record):
    step_id: str
    category: str
    action: str
    paths: tuple[str, ...]
    evidence: tuple[str, ...]
    confidence: Confidence

    def __post_init__(self) -> None:
        for value, label in (
            (self.step_id, "impact implementation step id"),
            (self.category, "impact implementation step category"),
            (self.action, "impact implementation step action"),
        ):
            _required(value, label)
        if not self.paths or not self.evidence:
            raise ValueError("impact implementation steps require paths and evidence")


@dataclass(frozen=True, slots=True)
class ImpactUnknown(_Record):
    code: str
    reason: str

    def __post_init__(self) -> None:
        _required(self.code, "impact unknown code")
        _required(self.reason, "impact unknown reason")


@dataclass(frozen=True, slots=True)
class ImpactOmissions(_Record):
    symbols: int
    dependants: int
    tests: int
    verifications: int

    def __post_init__(self) -> None:
        for name in ("symbols", "dependants", "tests", "verifications"):
            _non_negative(getattr(self, name), f"impact omissions {name}")


@dataclass(frozen=True, slots=True)
class InspectImpactResponse:
    project: ProjectIdentity
    changed_paths: tuple[str, ...]
    changed_symbols: tuple[ImpactSymbol, ...]
    dependants: tuple[ImpactDependant, ...]
    relationship_impacts: tuple[ImpactRelationship, ...]
    task_term_matches: tuple[str, ...]
    affected_tests: tuple[ImpactTest, ...]
    verification_handoffs: tuple[ImpactVerificationHandoff, ...]
    implementation_steps: tuple[ImpactImplementationStep, ...]
    unknowns: tuple[ImpactUnknown, ...]
    omissions: ImpactOmissions
    confidence: Confidence
    truncated: bool
    truncation_reasons: tuple[str, ...]
    fingerprint: str
    schema_version: int = INSPECT_IMPACT_SCHEMA_VERSION
    tool: str = INSPECT_IMPACT_TOOL

    def __post_init__(self) -> None:
        if self.schema_version != INSPECT_IMPACT_SCHEMA_VERSION:
            raise ValueError("inspect_impact schema_version must be 1")
        if self.tool != INSPECT_IMPACT_TOOL:
            raise ValueError("inspect_impact tool identity is fixed")
        if not self.changed_paths:
            raise ValueError("inspect_impact changed_paths must not be empty")
        if self.truncated != bool(self.truncation_reasons):
            raise ValueError("inspect_impact truncation state is inconsistent")
        if len(self.fingerprint) != 64 or any(c not in "0123456789abcdef" for c in self.fingerprint):
            raise ValueError("impact fingerprint must be 64 lowercase hexadecimal characters")

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "tool": self.tool,
            "project": self.project.to_json_dict(),
            "changed_paths": list(self.changed_paths),
            "changed_symbols": _json(self.changed_symbols),
            "dependants": _json(self.dependants),
            "relationship_impacts": _json(self.relationship_impacts),
            "task_term_matches": list(self.task_term_matches),
            "affected_tests": _json(self.affected_tests),
            "verification_handoffs": _json(self.verification_handoffs),
            "implementation_steps": _json(self.implementation_steps),
            "unknowns": _json(self.unknowns),
            "omissions": self.omissions.to_json_dict(),
            "confidence": self.confidence.value,
            "truncated": self.truncated,
            "truncation_reasons": list(self.truncation_reasons),
            "fingerprint": self.fingerprint,
        }


__all__ = [
    "ImpactBudget",
    "ImpactDependant",
    "ImpactImplementationStep",
    "ImpactOmissions",
    "ImpactRelationship",
    "ImpactSymbol",
    "ImpactTest",
    "ImpactUnknown",
    "ImpactVerificationHandoff",
    "InspectImpactRequest",
    "InspectImpactResponse",
]
