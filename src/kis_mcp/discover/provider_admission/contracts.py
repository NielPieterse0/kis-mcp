from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields
from enum import StrEnum
from typing import Any

from ..contracts import Confidence, ProjectIdentity

PROVIDER_ADMISSION_SCHEMA_VERSION = 1
PROVIDER_ADMISSION_TOOL = "inspect_provider_candidate"


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


def _hex_digest(value: str, label: str) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ValueError(f"{label} must be 64 lowercase hexadecimal characters")


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
class ProviderAdmissionBudget(_Record):
    max_capabilities: int
    max_evidence: int
    max_risks: int
    max_steps: int

    def __post_init__(self) -> None:
        for name in ("max_capabilities", "max_evidence", "max_risks", "max_steps"):
            _positive(getattr(self, name), f"provider admission budget {name}")


@dataclass(frozen=True, slots=True)
class ProviderAdmissionRequest(_Record):
    project: str
    manifest_path: str
    budget: ProviderAdmissionBudget

    def __post_init__(self) -> None:
        _required(self.project, "provider admission project")
        _required(self.manifest_path, "provider admission manifest_path")
        if not isinstance(self.budget, ProviderAdmissionBudget):
            raise ValueError("provider admission budget must be ProviderAdmissionBudget")


@dataclass(frozen=True, slots=True)
class ProviderEvidence(_Record):
    kind: str
    path: str
    summary: str
    provenance: str = "candidate_manifest"

    def __post_init__(self) -> None:
        for value, label in (
            (self.kind, "provider evidence kind"),
            (self.path, "provider evidence path"),
            (self.summary, "provider evidence summary"),
            (self.provenance, "provider evidence provenance"),
        ):
            _required(value, label)


@dataclass(frozen=True, slots=True)
class ProviderCandidate(_Record):
    candidate_id: str
    name: str
    provider_type: str
    revision: str
    license: str | None
    maintainer: str
    capabilities: tuple[str, ...]
    requested_effects: tuple[str, ...]
    authentication: str
    installation: str
    protocols: tuple[str, ...]
    platforms: tuple[str, ...]
    schema_present: bool
    health_contract_present: bool
    deterministic: bool
    conformance_tests: tuple[str, ...]
    evidence: tuple[ProviderEvidence, ...]
    overlaps: tuple[str, ...]
    manifest_path: str
    content_digest: str
    provenance: str = "checked_in_candidate_manifest"

    def __post_init__(self) -> None:
        for value, label in (
            (self.candidate_id, "provider candidate id"),
            (self.name, "provider candidate name"),
            (self.provider_type, "provider candidate type"),
            (self.revision, "provider candidate revision"),
            (self.maintainer, "provider candidate maintainer"),
            (self.authentication, "provider candidate authentication"),
            (self.installation, "provider candidate installation"),
            (self.manifest_path, "provider candidate manifest path"),
            (self.provenance, "provider candidate provenance"),
        ):
            _required(value, label)
        if self.license is not None:
            _required(self.license, "provider candidate license")
        if self.provider_type not in {"mcp_server", "tool", "provider"}:
            raise ValueError("provider candidate type is unsupported")
        if self.authentication not in {"none", "operator_injected", "provider_managed"}:
            raise ValueError("provider candidate authentication is unsupported")
        if self.installation not in {"bundled", "manual", "external_command"}:
            raise ValueError("provider candidate installation is unsupported")
        _hex_digest(self.content_digest, "provider candidate content_digest")


@dataclass(frozen=True, slots=True)
class ProviderRisk(_Record):
    code: str
    severity: str
    reason: str
    provenance: str = "candidate_manifest_assessment"

    def __post_init__(self) -> None:
        for value, label in (
            (self.code, "provider risk code"),
            (self.reason, "provider risk reason"),
            (self.provenance, "provider risk provenance"),
        ):
            _required(value, label)
        if self.severity not in {"low", "medium", "high"}:
            raise ValueError("provider risk severity is unsupported")


@dataclass(frozen=True, slots=True)
class ProviderAdmissionHandoff(_Record):
    request_id: str
    candidate_id: str
    decision: str
    requested_capabilities: tuple[str, ...]
    requested_effects: tuple[str, ...]
    unresolved_risks: tuple[str, ...]
    required_evidence: tuple[str, ...]
    provenance: str = "discover_provider_admission"

    def __post_init__(self) -> None:
        for value, label in (
            (self.request_id, "provider admission request id"),
            (self.candidate_id, "provider admission candidate id"),
            (self.provenance, "provider admission provenance"),
        ):
            _required(value, label)
        if self.decision != "pending_govern":
            raise ValueError("provider admission decision must remain pending_govern")


@dataclass(frozen=True, slots=True)
class ProviderConformanceStep(_Record):
    step_id: str
    category: str
    description: str
    execution_available: bool = False
    provenance: str = "discover_non_executing_work_plan"

    def __post_init__(self) -> None:
        for value, label in (
            (self.step_id, "provider conformance step id"),
            (self.category, "provider conformance category"),
            (self.description, "provider conformance description"),
            (self.provenance, "provider conformance provenance"),
        ):
            _required(value, label)
        if self.execution_available is not False:
            raise ValueError("provider conformance steps must be non-executing")


@dataclass(frozen=True, slots=True)
class ProviderUnknown(_Record):
    code: str
    reason: str

    def __post_init__(self) -> None:
        _required(self.code, "provider unknown code")
        _required(self.reason, "provider unknown reason")


@dataclass(frozen=True, slots=True)
class ProviderAdmissionOmissions(_Record):
    capabilities: int
    evidence: int
    risks: int
    steps: int

    def __post_init__(self) -> None:
        for name in ("capabilities", "evidence", "risks", "steps"):
            _non_negative(getattr(self, name), f"provider admission omissions {name}")


@dataclass(frozen=True, slots=True)
class ProviderAdmissionResponse:
    project: ProjectIdentity
    candidate: ProviderCandidate
    risks: tuple[ProviderRisk, ...]
    admission_request: ProviderAdmissionHandoff
    conformance_plan: tuple[ProviderConformanceStep, ...]
    unknowns: tuple[ProviderUnknown, ...]
    omissions: ProviderAdmissionOmissions
    confidence: Confidence
    truncated: bool
    truncation_reasons: tuple[str, ...]
    fingerprint: str
    schema_version: int = PROVIDER_ADMISSION_SCHEMA_VERSION
    tool: str = PROVIDER_ADMISSION_TOOL

    def __post_init__(self) -> None:
        if self.schema_version != PROVIDER_ADMISSION_SCHEMA_VERSION:
            raise ValueError("provider admission schema_version must be 1")
        if self.tool != PROVIDER_ADMISSION_TOOL:
            raise ValueError("provider admission tool identity is fixed")
        if self.truncated != bool(self.truncation_reasons):
            raise ValueError("provider admission truncation state is inconsistent")
        _hex_digest(self.fingerprint, "provider admission fingerprint")

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "tool": self.tool,
            "project": self.project.to_json_dict(),
            "candidate": self.candidate.to_json_dict(),
            "risks": _json(self.risks),
            "admission_request": self.admission_request.to_json_dict(),
            "conformance_plan": _json(self.conformance_plan),
            "unknowns": _json(self.unknowns),
            "omissions": self.omissions.to_json_dict(),
            "confidence": self.confidence.value,
            "truncated": self.truncated,
            "truncation_reasons": list(self.truncation_reasons),
            "fingerprint": self.fingerprint,
        }


__all__ = [
    "ProviderAdmissionBudget",
    "ProviderAdmissionHandoff",
    "ProviderAdmissionOmissions",
    "ProviderAdmissionRequest",
    "ProviderAdmissionResponse",
    "ProviderCandidate",
    "ProviderConformanceStep",
    "ProviderEvidence",
    "ProviderRisk",
    "ProviderUnknown",
]
