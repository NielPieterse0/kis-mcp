from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

CHANGE_EXECUTION_SCHEMA_VERSION = 2
CHANGE_EXECUTION_CONTRACT = "change-execution-result-v2"


@dataclass(frozen=True, slots=True)
class ChangeExecutionStepResult:
    step_id: str
    kind: str
    status: str
    payload: Mapping[str, Any] | None = None
    error_code: str | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        if not self.step_id.strip():
            raise ValueError("change execution step_id must not be empty")
        if self.kind not in {"verification", "review"}:
            raise ValueError("change execution step kind is unsupported")
        if self.status not in {"passed", "failed", "incomplete", "completed", "error"}:
            raise ValueError("change execution step status is unsupported")
        if self.status == "error" and (not self.error_code or not self.reason):
            raise ValueError("error steps require error_code and reason")
    def to_json_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "step_id": self.step_id,
            "kind": self.kind,
            "status": self.status,
            "payload": dict(self.payload) if self.payload is not None else None,
            "error_code": self.error_code,
            "reason": self.reason,
        }
        return result


@dataclass(frozen=True, slots=True)
class ChangeExecutionResult:
    project: str
    source_fingerprint: str
    complexity: str
    risk_triggers: tuple[str, ...]
    selection: Mapping[str, Any]
    verifications: tuple[ChangeExecutionStepResult, ...]
    reviews: tuple[ChangeExecutionStepResult, ...]
    status: str
    verification_failed_count: int
    verification_incomplete_count: int
    review_error_count: int
    schema_version: int = CHANGE_EXECUTION_SCHEMA_VERSION
    contract: str = CHANGE_EXECUTION_CONTRACT
    tool: str = "execute_change_workflow"

    def __post_init__(self) -> None:
        if self.schema_version != CHANGE_EXECUTION_SCHEMA_VERSION:
            raise ValueError("change execution schema_version must be 2")
        if self.contract != CHANGE_EXECUTION_CONTRACT or self.tool != "execute_change_workflow":
            raise ValueError("change execution result identity is fixed")
        if not self.project.strip():
            raise ValueError("change execution project must not be empty")
        if self.complexity not in {"small", "medium", "large"}:
            raise ValueError("change execution complexity is unsupported")
        if tuple(sorted(set(self.risk_triggers))) != self.risk_triggers:
            raise ValueError("change execution risk_triggers must be unique and sorted")
        if len(self.source_fingerprint) != 64 or any(
            character not in "0123456789abcdef" for character in self.source_fingerprint
        ):
            raise ValueError("change execution source_fingerprint must be 64 lowercase hex characters")
        if self.status not in {"passed", "failed", "incomplete"}:
            raise ValueError("change execution result status is unsupported")
        for count in (
            self.verification_failed_count,
            self.verification_incomplete_count,
            self.review_error_count,
        ):
            if isinstance(count, bool) or count < 0:
                raise ValueError("change execution counts must be non-negative integers")

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "contract": self.contract,
            "tool": self.tool,
            "project": self.project,
            "source_fingerprint": self.source_fingerprint,
            "complexity": self.complexity,
            "risk_triggers": list(self.risk_triggers),
            "selection": dict(self.selection),
            "verifications": [item.to_json_dict() for item in self.verifications],
            "reviews": [item.to_json_dict() for item in self.reviews],
            "status": self.status,
            "verification_failed_count": self.verification_failed_count,
            "verification_incomplete_count": self.verification_incomplete_count,
            "review_error_count": self.review_error_count,
        }


__all__ = [
    "CHANGE_EXECUTION_CONTRACT",
    "CHANGE_EXECUTION_SCHEMA_VERSION",
    "ChangeExecutionResult",
    "ChangeExecutionStepResult",
]
