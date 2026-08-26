from __future__ import annotations

from dataclasses import dataclass
from typing import Any

VERIFICATION_RESULT_SCHEMA_VERSION = 1
VERIFICATION_RESULT_CONTRACT = "verification-result-v1"
VERIFICATION_SELECTION_SCHEMA_VERSION = 1
VERIFICATION_SELECTION_CONTRACT = "verification-selection-v1"


@dataclass(frozen=True, slots=True)
class VerificationResult:
    verification_id: str
    title: str
    category: str
    source_path: str
    profile: str
    arguments: tuple[str, ...]
    command_identity: str
    status: str
    exit_code: int | None
    duration_ms: int
    evidence: str
    failure_classification: str
    truncated: bool
    schema_version: int = VERIFICATION_RESULT_SCHEMA_VERSION
    contract: str = VERIFICATION_RESULT_CONTRACT
    tool: str = "run_verification"

    def __post_init__(self) -> None:
        if self.schema_version != VERIFICATION_RESULT_SCHEMA_VERSION:
            raise ValueError("verification result schema_version must be 1")
        if self.contract != VERIFICATION_RESULT_CONTRACT or self.tool != "run_verification":
            raise ValueError("verification result identity is fixed")
        if self.status not in {"passed", "failed", "incomplete"}:
            raise ValueError("verification result status is unsupported")
        if self.failure_classification not in {
            "none",
            "verification_failed",
            "timeout_or_incomplete",
            "stalled",
        }:
            raise ValueError("verification failure classification is unsupported")
        if self.duration_ms < 0:
            raise ValueError("verification duration must not be negative")

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "contract": self.contract,
            "tool": self.tool,
            "verification_id": self.verification_id,
            "title": self.title,
            "category": self.category,
            "source_path": self.source_path,
            "profile": self.profile,
            "arguments": list(self.arguments),
            "command_identity": self.command_identity,
            "status": self.status,
            "exit_code": self.exit_code,
            "duration_ms": self.duration_ms,
            "evidence": self.evidence,
            "failure_classification": self.failure_classification,
            "truncated": self.truncated,
        }


@dataclass(frozen=True, slots=True)
class VerificationSelectionItem:
    verification_id: str
    category: str
    reason: str
    profile: str
    source_path: str
    execution_available: bool = False

    def __post_init__(self) -> None:
        if self.execution_available:
            raise ValueError("verification selection must not grant execution authority")

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "verification_id": self.verification_id,
            "category": self.category,
            "reason": self.reason,
            "profile": self.profile,
            "source_path": self.source_path,
            "execution_available": self.execution_available,
        }


@dataclass(frozen=True, slots=True)
class VerificationSelectionIssue:
    verification_id: str
    code: str
    reason: str

    def to_json_dict(self) -> dict[str, str]:
        return {
            "verification_id": self.verification_id,
            "code": self.code,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class VerificationSelectionResult:
    project: str
    source_fingerprint: str
    selected: tuple[VerificationSelectionItem, ...]
    skipped: tuple[VerificationSelectionIssue, ...]
    omitted_count: int
    truncated: bool
    schema_version: int = VERIFICATION_SELECTION_SCHEMA_VERSION
    contract: str = VERIFICATION_SELECTION_CONTRACT
    tool: str = "select_change_verification"

    def __post_init__(self) -> None:
        if self.schema_version != VERIFICATION_SELECTION_SCHEMA_VERSION:
            raise ValueError("verification selection schema_version must be 1")
        if self.contract != VERIFICATION_SELECTION_CONTRACT or self.tool != "select_change_verification":
            raise ValueError("verification selection identity is fixed")
        if not self.project.strip():
            raise ValueError("verification selection project must not be empty")
        if len(self.source_fingerprint) != 64 or any(
            character not in "0123456789abcdef" for character in self.source_fingerprint
        ):
            raise ValueError("verification selection source_fingerprint must be 64 lowercase hex characters")
        if isinstance(self.omitted_count, bool) or self.omitted_count < 0:
            raise ValueError("verification selection omitted_count must be non-negative")

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "contract": self.contract,
            "tool": self.tool,
            "project": self.project,
            "source_fingerprint": self.source_fingerprint,
            "selected": [item.to_json_dict() for item in self.selected],
            "skipped": [item.to_json_dict() for item in self.skipped],
            "omitted_count": self.omitted_count,
            "truncated": self.truncated,
        }


__all__ = [
    "VERIFICATION_RESULT_CONTRACT",
    "VERIFICATION_RESULT_SCHEMA_VERSION",
    "VERIFICATION_SELECTION_CONTRACT",
    "VERIFICATION_SELECTION_SCHEMA_VERSION",
    "VerificationResult",
    "VerificationSelectionIssue",
    "VerificationSelectionItem",
    "VerificationSelectionResult",
]
