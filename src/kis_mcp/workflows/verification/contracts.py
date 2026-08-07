from __future__ import annotations

from dataclasses import dataclass
from typing import Any

VERIFICATION_RESULT_SCHEMA_VERSION = 1
VERIFICATION_RESULT_CONTRACT = "verification-result-v1"


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


__all__ = [
    "VERIFICATION_RESULT_CONTRACT",
    "VERIFICATION_RESULT_SCHEMA_VERSION",
    "VerificationResult",
]
