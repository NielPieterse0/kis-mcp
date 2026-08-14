from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
import json
from typing import Any


class WorkManagementErrorCode(StrEnum):
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    PROJECT_NOT_COMMISSIONED = "project_not_commissioned"
    INVENTORY_INCOMPLETE = "inventory_incomplete"
    CONFLICT = "conflict"
    INVALID_TRANSITION = "invalid_transition"
    NOT_FOUND = "not_found"
    INVALID_REQUEST = "invalid_request"
    INTERNAL = "internal"


@dataclass(frozen=True, slots=True)
class WorkManagementResultEnvelope:
    result: Any
    project_id: str
    repository: str | None = None
    issue_number: int | None = None
    authority: str = "configured_work_management_backend"
    complete: bool = True
    truncated: bool = False
    warnings: tuple[str, ...] = ()
    next_actions: tuple[str, ...] = ()
    observed_at: str = ""
    schema_version: int = 1

    def __post_init__(self) -> None:
        if not self.project_id.strip():
            raise ValueError("project_id must be populated")
        if not self.observed_at:
            object.__setattr__(self, "observed_at", datetime.now(UTC).isoformat())

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "observed_at": self.observed_at,
            "resolved_target": {
                "project_id": self.project_id,
                "repository": self.repository,
                "issue_number": self.issue_number,
            },
            "provenance": {
                "authority": self.authority,
                "complete": self.complete,
                "truncated": self.truncated,
                "warnings": list(self.warnings),
            },
            "result": self.result,
            "next_actions": list(self.next_actions),
        }


def result_envelope(
    result: Any,
    project_id: str,
    *,
    repository: str | None = None,
    issue_number: int | None = None,
    complete: bool = True,
    truncated: bool = False,
    warnings: tuple[str, ...] = (),
    next_actions: tuple[str, ...] = (),
) -> dict[str, Any]:
    return WorkManagementResultEnvelope(
        result=result,
        project_id=project_id,
        repository=repository,
        issue_number=issue_number,
        complete=complete,
        truncated=truncated,
        warnings=warnings,
        next_actions=next_actions,
    ).to_json_dict()


def classify_work_management_error(exc: Exception) -> WorkManagementErrorCode:
    explicit = getattr(exc, "error_code", None)
    if explicit == WorkManagementErrorCode.PROVIDER_UNAVAILABLE.value:
        return WorkManagementErrorCode.PROVIDER_UNAVAILABLE
    if explicit == WorkManagementErrorCode.PROJECT_NOT_COMMISSIONED.value:
        return WorkManagementErrorCode.PROJECT_NOT_COMMISSIONED
    text = str(exc).casefold()
    if "truncated" in text or "incomplete" in text:
        return WorkManagementErrorCode.INVENTORY_INCOMPLETE
    if "already claimed" in text or "expected_owner" in text or "conflict" in text:
        return WorkManagementErrorCode.CONFLICT
    if "cannot be" in text and ("transition" in text or "work state" in text):
        return WorkManagementErrorCode.INVALID_TRANSITION
    if "not found" in text or "not present" in text:
        return WorkManagementErrorCode.NOT_FOUND
    if isinstance(exc, ValueError):
        return WorkManagementErrorCode.INVALID_REQUEST
    return WorkManagementErrorCode.INTERNAL


def error_document(operation: str, exc: Exception) -> dict[str, Any]:
    code = classify_work_management_error(exc)
    retryable = code in {
        WorkManagementErrorCode.PROVIDER_UNAVAILABLE,
        WorkManagementErrorCode.INVENTORY_INCOMPLETE,
    }
    return {
        "schema_version": 1,
        "operation": operation,
        "error_code": code.value,
        "error_type": type(exc).__name__,
        "reason": str(exc),
        "retryable": retryable,
        "authority": "configured_work_management_backend",
    }


def error_json(operation: str, exc: Exception) -> str:
    return json.dumps(
        error_document(operation, exc),
        sort_keys=True,
        separators=(",", ":"),
    )


__all__ = [
    "WorkManagementErrorCode",
    "WorkManagementResultEnvelope",
    "classify_work_management_error",
    "error_document",
    "error_json",
    "result_envelope",
]
