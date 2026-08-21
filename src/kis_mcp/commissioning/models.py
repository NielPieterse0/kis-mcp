from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ClassificationState(str, Enum):
    NOT_REQUIRED = "not_required"
    REQUIRED = "required"
    BLOCKED_AMBIGUOUS = "blocked_ambiguous"


class IntakeDisposition(str, Enum):
    EXISTING = "existing"
    CREATED = "created"


@dataclass(frozen=True, slots=True)
class LandedChangeEvidence:
    repository: str
    source_issue: int
    source_pr: int
    merge_sha: str
    change_id: str
    changed_paths: tuple[str, ...]
    risk_triggers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CommissioningObligation:
    surface_id: str
    commissioning_key: str
    runtime_instance: str
    refresh_rule: str
    probe_id: str
    verification_procedure: str
    expected_invariant: str
    evidence_target: str
    terminal_success_criterion: str
    matched_paths: tuple[str, ...]
    matched_risk_triggers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ChangeClassification:
    state: ClassificationState
    obligations: tuple[CommissioningObligation, ...] = ()
    ambiguous_risk_triggers: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CommissioningIntakeOutcome:
    surface_id: str
    commissioning_key: str
    disposition: IntakeDisposition
    issue_number: int
    issue_url: str | None = None
    matching_issue_numbers: tuple[int, ...] = ()


__all__ = [
    "ChangeClassification",
    "ClassificationState",
    "CommissioningIntakeOutcome",
    "CommissioningObligation",
    "IntakeDisposition",
    "LandedChangeEvidence",
]
