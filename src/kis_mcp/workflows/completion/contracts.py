from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

COMPLETION_SCHEMA_VERSION = 1
COMPLETION_CONTRACT = "completion-result-v1"
COMPLETION_RECEIPT_CONTRACT = "completion-operation-receipt-v1"
_OPERATION_STATES = frozenset({"not_started", "in_progress", "applied", "failed", "unknown"})


def _validate_operation_fields(
    *,
    operation_id: str,
    operation_state: str,
    elapsed_ms: int,
    stage_timings_ms: Mapping[str, int],
) -> None:
    if not operation_id.startswith("prp-") or len(operation_id) != 68:
        raise ValueError("completion operation_id must be a prp-prefixed SHA-256 identity")
    if operation_state not in _OPERATION_STATES:
        raise ValueError("completion operation_state is unsupported")
    if isinstance(elapsed_ms, bool) or not isinstance(elapsed_ms, int) or elapsed_ms < 0:
        raise ValueError("completion elapsed_ms must be a non-negative integer")
    for stage, duration in stage_timings_ms.items():
        if not isinstance(stage, str) or not stage:
            raise ValueError("completion stage timing name must not be empty")
        if isinstance(duration, bool) or not isinstance(duration, int) or duration < 0:
            raise ValueError("completion stage timing must be a non-negative integer")


@dataclass(frozen=True, slots=True)
class CompletionResult:
    project_id: str
    source_commit_sha: str
    published_head_sha: str
    branch: str
    execution: Mapping[str, Any]
    publication: Mapping[str, Any]
    pull_request: Mapping[str, Any]
    operation_id: str
    operation_state: str
    elapsed_ms: int
    stage_timings_ms: Mapping[str, int]
    status: str = "reviewable"
    schema_version: int = COMPLETION_SCHEMA_VERSION
    contract: str = COMPLETION_CONTRACT
    tool: str = "prepare_reviewable_pull_request"

    def __post_init__(self) -> None:
        if self.schema_version != COMPLETION_SCHEMA_VERSION:
            raise ValueError("completion schema_version must be 1")
        if self.contract != COMPLETION_CONTRACT or self.tool != "prepare_reviewable_pull_request":
            raise ValueError("completion result identity is fixed")
        if not self.project_id.strip() or not self.branch.strip():
            raise ValueError("completion project_id and branch must not be empty")
        for label, value in (
            ("source_commit_sha", self.source_commit_sha),
            ("published_head_sha", self.published_head_sha),
        ):
            if len(value) != 40 or any(character not in "0123456789abcdef" for character in value):
                raise ValueError(f"completion {label} must be 40 lowercase hex characters")
        if self.status != "reviewable" or self.operation_state != "applied":
            raise ValueError("successful completion must be reviewable and applied")
        _validate_operation_fields(
            operation_id=self.operation_id,
            operation_state=self.operation_state,
            elapsed_ms=self.elapsed_ms,
            stage_timings_ms=self.stage_timings_ms,
        )

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "contract": self.contract,
            "tool": self.tool,
            "project_id": self.project_id,
            "source_commit_sha": self.source_commit_sha,
            "published_head_sha": self.published_head_sha,
            "branch": self.branch,
            "status": self.status,
            "operation_id": self.operation_id,
            "operation_state": self.operation_state,
            "elapsed_ms": self.elapsed_ms,
            "stage_timings_ms": dict(self.stage_timings_ms),
            "execution": dict(self.execution),
            "publication": dict(self.publication),
            "pull_request": dict(self.pull_request),
        }


@dataclass(frozen=True, slots=True)
class CompletionReceipt:
    project_id: str
    source_commit_sha: str
    branch: str
    operation_id: str
    operation_state: str
    stage: str
    elapsed_ms: int
    stage_timings_ms: Mapping[str, int]
    completed_steps: tuple[str, ...] = ()
    execution: Mapping[str, Any] = field(default_factory=dict)
    publication: Mapping[str, Any] = field(default_factory=dict)
    pull_request: Mapping[str, Any] = field(default_factory=dict)
    schema_version: int = COMPLETION_SCHEMA_VERSION
    contract: str = COMPLETION_RECEIPT_CONTRACT
    tool: str = "prepare_reviewable_pull_request"

    def __post_init__(self) -> None:
        if self.schema_version != COMPLETION_SCHEMA_VERSION:
            raise ValueError("completion receipt schema_version must be 1")
        if self.contract != COMPLETION_RECEIPT_CONTRACT or self.tool != "prepare_reviewable_pull_request":
            raise ValueError("completion receipt identity is fixed")
        if not self.project_id.strip() or not self.branch.strip() or not self.stage.strip():
            raise ValueError("completion receipt identity fields must not be empty")
        if len(self.source_commit_sha) != 40 or any(
            character not in "0123456789abcdef" for character in self.source_commit_sha
        ):
            raise ValueError("completion receipt source_commit_sha must be 40 lowercase hex characters")
        _validate_operation_fields(
            operation_id=self.operation_id,
            operation_state=self.operation_state,
            elapsed_ms=self.elapsed_ms,
            stage_timings_ms=self.stage_timings_ms,
        )

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "contract": self.contract,
            "tool": self.tool,
            "project_id": self.project_id,
            "source_commit_sha": self.source_commit_sha,
            "branch": self.branch,
            "operation_id": self.operation_id,
            "operation_state": self.operation_state,
            "stage": self.stage,
            "completed_steps": list(self.completed_steps),
            "elapsed_ms": self.elapsed_ms,
            "stage_timings_ms": dict(self.stage_timings_ms),
            "execution": dict(self.execution),
            "publication": dict(self.publication),
            "pull_request": dict(self.pull_request),
        }


__all__ = [
    "COMPLETION_CONTRACT",
    "COMPLETION_RECEIPT_CONTRACT",
    "COMPLETION_SCHEMA_VERSION",
    "CompletionReceipt",
    "CompletionResult",
]
