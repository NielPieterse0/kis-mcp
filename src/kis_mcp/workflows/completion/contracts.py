from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

COMPLETION_SCHEMA_VERSION = 1
COMPLETION_CONTRACT = "completion-result-v1"


@dataclass(frozen=True, slots=True)
class CompletionResult:
    project_id: str
    source_commit_sha: str
    published_head_sha: str
    branch: str
    execution: Mapping[str, Any]
    publication: Mapping[str, Any]
    pull_request: Mapping[str, Any]
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
            if len(value) != 40 or any(
                character not in "0123456789abcdef" for character in value
            ):
                raise ValueError(f"completion {label} must be 40 lowercase hex characters")
        if self.status != "reviewable":
            raise ValueError("completion status must be reviewable")

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
            "execution": dict(self.execution),
            "publication": dict(self.publication),
            "pull_request": dict(self.pull_request),
        }


__all__ = ["COMPLETION_CONTRACT", "COMPLETION_SCHEMA_VERSION", "CompletionResult"]
