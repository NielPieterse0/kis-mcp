from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields
from enum import StrEnum
from typing import Any

PUBLIC_SCHEMA_VERSION = 1
INSPECT_PROJECT_TOOL = "inspect_project"


class Confidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TrustState(StrEnum):
    TRUSTED = "trusted"
    UNTRUSTED = "untrusted"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


class Freshness(StrEnum):
    CURRENT = "current"
    STALE = "stale"
    UNKNOWN = "unknown"


class ProvenanceKind(StrEnum):
    DECLARED = "declared"
    OBSERVED = "observed"
    CONVENTIONAL = "conventional"
    INFERRED = "inferred"
    REMOTE_OBSERVED = "remote_observed"
    GOVERNANCE_REQUIRED = "governance_required"
    RECOMMENDED = "recommended"


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


def _required_text(value: str, label: str) -> str:
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


def _json_value(value: Any) -> Any:
    if hasattr(value, "to_json_dict"):
        return value.to_json_dict()
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise ValueError(f"value is not JSON-compatible: {type(value).__name__}")


class _JsonRecord:
    def to_json_dict(self) -> dict[str, Any]:
        return {field.name: _json_value(getattr(self, field.name)) for field in fields(self)}


@dataclass(frozen=True, slots=True)
class EvidenceSource(_JsonRecord):
    kind: str
    provider: str
    identifier: str
    revision: str | None = None

    def __post_init__(self) -> None:
        _required_text(self.kind, "evidence source kind")
        _required_text(self.provider, "evidence source provider")
        _required_text(self.identifier, "evidence source identifier")


@dataclass(frozen=True, slots=True)
class Provenance(_JsonRecord):
    kind: ProvenanceKind
    source_id: str

    def __post_init__(self) -> None:
        _required_text(self.source_id, "provenance source_id")


@dataclass(frozen=True, slots=True)
class EvidenceItem(_JsonRecord):
    id: str
    kind: str
    subject: str
    source: EvidenceSource
    provenance: Provenance
    location: Mapping[str, Any]
    trust: TrustState
    confidence: Confidence
    freshness: Freshness
    summary: str
    details: Mapping[str, Any]
    truncated: bool = False

    def __post_init__(self) -> None:
        _required_text(self.id, "evidence id")
        _required_text(self.kind, "evidence kind")
        _required_text(self.subject, "evidence subject")
        _required_text(self.summary, "evidence summary")


@dataclass(frozen=True, slots=True)
class EvidenceBudget(_JsonRecord):
    max_files: int
    max_directories: int
    max_total_bytes: int
    max_evidence: int
    max_output_chars: int
    max_depth: int

    def __post_init__(self) -> None:
        for name in (
            "max_files",
            "max_directories",
            "max_total_bytes",
            "max_evidence",
            "max_output_chars",
            "max_depth",
        ):
            _positive(getattr(self, name), name)


@dataclass(frozen=True, slots=True)
class TruncationState(_JsonRecord):
    truncated: bool
    reasons: tuple[str, ...]
    counters: Mapping[str, int]

    def __post_init__(self) -> None:
        if any(not reason.strip() for reason in self.reasons):
            raise ValueError("truncation reasons must be non-empty strings")
        for key, value in self.counters.items():
            _required_text(str(key), "truncation counter name")
            _non_negative(value, f"truncation counter {key}")


@dataclass(frozen=True, slots=True)
class ProjectIdentity(_JsonRecord):
    project_id: str
    canonical_path: str
    repository_root: str
    git_root: str | None
    remote_identity: str | None

    def __post_init__(self) -> None:
        _required_text(self.project_id, "project id")
        _required_text(self.canonical_path, "canonical path")
        _required_text(self.repository_root, "repository root")


@dataclass(frozen=True, slots=True)
class ProjectTopology(_JsonRecord):
    files: tuple[str, ...]
    directories: tuple[str, ...]
    excluded_paths: tuple[str, ...]
    file_count: int
    directory_count: int

    def __post_init__(self) -> None:
        _non_negative(self.file_count, "file_count")
        _non_negative(self.directory_count, "directory_count")


@dataclass(frozen=True, slots=True)
class ManifestEvidence(_JsonRecord):
    path: str
    kind: str
    ecosystem: str
    package_manager: str | None
    workspace: bool
    confidence: Confidence
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _required_text(self.path, "manifest path")
        _required_text(self.kind, "manifest kind")
        _required_text(self.ecosystem, "manifest ecosystem")


@dataclass(frozen=True, slots=True)
class VerificationDeclaration(_JsonRecord):
    id: str
    category: str
    title: str
    authority: str
    execution_available: bool
    source_path: str
    profile: str
    arguments: tuple[str, ...]
    provenance: ProvenanceKind
    confidence: Confidence
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _required_text(self.id, "verification id")
        _required_text(self.category, "verification category")
        _required_text(self.title, "verification title")
        _required_text(self.authority, "verification authority")
        _required_text(self.source_path, "verification source path")
        _required_text(self.profile, "verification profile")
        if self.authority == "discovered_only" and self.execution_available:
            raise ValueError("discovered-only verification cannot be executable")


@dataclass(frozen=True, slots=True)
class GitSummary(_JsonRecord):
    available: bool
    repository: bool
    branch: str | None
    detached: bool
    head: str | None
    status: str
    tracked_files: int
    remote: str | None
    recent_commits: tuple[Mapping[str, str], ...] = ()
    diagnostics: tuple[Mapping[str, Any], ...] = ()
    truncated: bool = False

    def __post_init__(self) -> None:
        _required_text(self.status, "Git status")
        _non_negative(self.tracked_files, "tracked_files")


@dataclass(frozen=True, slots=True)
class ProjectDiagnostic(_JsonRecord):
    code: str
    message: str
    severity: Severity = Severity.WARNING
    path: str | None = None

    def __post_init__(self) -> None:
        _required_text(self.code, "diagnostic code")
        _required_text(self.message, "diagnostic message")


@dataclass(frozen=True, slots=True)
class Finding(_JsonRecord):
    id: str
    code: str
    title: str
    severity: Severity
    scope: str
    observation: str
    impact: str
    evidence_ids: tuple[str, ...]
    confidence: Confidence
    remediation: str
    owning_plane: str

    def __post_init__(self) -> None:
        for value, label in (
            (self.id, "finding id"),
            (self.code, "finding code"),
            (self.title, "finding title"),
            (self.scope, "finding scope"),
            (self.observation, "finding observation"),
            (self.impact, "finding impact"),
            (self.remediation, "finding remediation"),
            (self.owning_plane, "finding owning plane"),
        ):
            _required_text(value, label)


@dataclass(frozen=True, slots=True)
class Recommendation(_JsonRecord):
    id: str
    category: str
    action: str
    rationale: str
    evidence_ids: tuple[str, ...]
    expected_benefit: str
    cost_class: str
    risks: tuple[str, ...]
    owning_plane: str

    def __post_init__(self) -> None:
        for value, label in (
            (self.id, "recommendation id"),
            (self.category, "recommendation category"),
            (self.action, "recommendation action"),
            (self.rationale, "recommendation rationale"),
            (self.expected_benefit, "recommendation benefit"),
            (self.cost_class, "recommendation cost class"),
            (self.owning_plane, "recommendation owning plane"),
        ):
            _required_text(value, label)


@dataclass(frozen=True, slots=True)
class Unknown(_JsonRecord):
    id: str
    code: str
    reason: str
    evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _required_text(self.id, "unknown id")
        _required_text(self.code, "unknown code")
        _required_text(self.reason, "unknown reason")


@dataclass(frozen=True, slots=True)
class Handoff(_JsonRecord):
    handoff_id: str
    target_plane: str
    workflow: str
    reason: str
    inputs: Mapping[str, Any]
    evidence_ids: tuple[str, ...]
    required_authority: tuple[str, ...]
    expected_result_contract: str

    def __post_init__(self) -> None:
        for value, label in (
            (self.handoff_id, "handoff id"),
            (self.target_plane, "handoff target plane"),
            (self.workflow, "handoff workflow"),
            (self.reason, "handoff reason"),
            (self.expected_result_contract, "handoff result contract"),
        ):
            _required_text(value, label)


@dataclass(frozen=True, slots=True)
class InspectProjectRequest(_JsonRecord):
    path: str
    limits: Mapping[str, int] | None = None

    def __post_init__(self) -> None:
        _required_text(self.path, "inspect project path")


@dataclass(frozen=True, slots=True)
class InspectProjectResponse:
    project: ProjectIdentity
    repository_atlas: Mapping[str, Any]
    code_atlas: Mapping[str, Any]
    verification: Mapping[str, Any]
    contracts: Mapping[str, Any]
    instructions: tuple[Mapping[str, Any], ...]
    git: GitSummary
    remote: Mapping[str, Any]
    providers: Mapping[str, Any]
    evidence: tuple[EvidenceItem, ...]
    findings: tuple[Finding | Mapping[str, Any], ...]
    recommendations: tuple[Recommendation | Mapping[str, Any], ...]
    handoffs: tuple[Handoff | Mapping[str, Any], ...]
    assumptions: tuple[Mapping[str, Any], ...]
    unknowns: tuple[Unknown | Mapping[str, Any], ...]
    confidence: Confidence
    truncated: bool
    truncation_reasons: tuple[str, ...]
    schema_version: int = PUBLIC_SCHEMA_VERSION
    tool: str = INSPECT_PROJECT_TOOL

    def __post_init__(self) -> None:
        if self.schema_version != PUBLIC_SCHEMA_VERSION:
            raise ValueError("inspect_project schema_version must be 1")
        if self.tool != INSPECT_PROJECT_TOOL:
            raise ValueError("inspect_project tool identity is fixed")

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "tool": self.tool,
            "project": self.project.to_json_dict(),
            "repository_atlas": _json_value(self.repository_atlas),
            "code_atlas": _json_value(self.code_atlas),
            "verification": _json_value(self.verification),
            "contracts": _json_value(self.contracts),
            "instructions": _json_value(self.instructions),
            "git": self.git.to_json_dict(),
            "remote": _json_value(self.remote),
            "providers": _json_value(self.providers),
            "evidence": _json_value(self.evidence),
            "findings": _json_value(self.findings),
            "recommendations": _json_value(self.recommendations),
            "handoffs": _json_value(self.handoffs),
            "assumptions": _json_value(self.assumptions),
            "unknowns": _json_value(self.unknowns),
            "confidence": self.confidence.value,
            "truncated": self.truncated,
            "truncation_reasons": list(self.truncation_reasons),
        }


__all__ = [
    "Confidence",
    "EvidenceBudget",
    "EvidenceItem",
    "EvidenceSource",
    "Finding",
    "Freshness",
    "GitSummary",
    "Handoff",
    "INSPECT_PROJECT_TOOL",
    "InspectProjectRequest",
    "InspectProjectResponse",
    "ManifestEvidence",
    "PUBLIC_SCHEMA_VERSION",
    "ProjectDiagnostic",
    "ProjectIdentity",
    "ProjectTopology",
    "Provenance",
    "ProvenanceKind",
    "Recommendation",
    "Severity",
    "TruncationState",
    "TrustState",
    "Unknown",
    "VerificationDeclaration",
]
