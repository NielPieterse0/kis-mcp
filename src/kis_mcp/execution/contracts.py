from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

EXECUTION_REQUEST_CONTRACT = "execution-request-v1"
EXECUTION_RESULT_CONTRACT = "execution-result-v1"
EXECUTION_SCHEMA_VERSION = 1

_LOGICAL_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_GIT_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_SUPPORTED_STATUSES = frozenset({"passed", "failed", "incomplete"})
_SUPPORTED_FAILURES = frozenset(
    {
        "none",
        "execution_failed",
        "timeout_or_incomplete",
        "backend_unavailable",
        "source_identity_required",
        "source_mismatch",
        "lifecycle_failed",
        "cleanup_failed",
        "profile_identity_mismatch",
    }
)


class ReadinessStatus(StrEnum):
    READY = "ready"
    UNAVAILABLE = "unavailable"


class ExecutionLifecycleState(StrEnum):
    REQUESTED = "requested"
    READINESS = "readiness"
    MATERIALIZING = "materializing"
    PROVISIONING = "provisioning"
    STARTING = "starting"
    TRANSFERRING = "transferring"
    EXECUTING = "executing"
    CAPTURING = "capturing"
    CLEANING = "cleaning"
    COMPLETED = "completed"
    QUARANTINED = "quarantined"
    INCOMPLETE = "incomplete"


class CleanupDisposition(StrEnum):
    NOT_REQUIRED = "not-required"
    DESTROYED = "destroyed"
    QUARANTINED = "quarantined"
    FAILED = "failed"


def _text(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _logical_id(value: str, label: str) -> str:
    normalized = _text(value, label)
    if _LOGICAL_ID.fullmatch(normalized) is None:
        raise ValueError(f"{label} must be a safe logical identifier")
    return normalized


@dataclass(frozen=True, slots=True)
class ExecutionReadiness:
    backend_id: str
    status: ReadinessStatus
    reason: str
    diagnostics: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "backend_id", _logical_id(self.backend_id, "backend_id"))
        object.__setattr__(self, "reason", _text(self.reason, "reason"))
        if not isinstance(self.status, ReadinessStatus):
            raise ValueError("readiness status is invalid")
        if not isinstance(self.diagnostics, tuple) or any(
            not isinstance(item, str) for item in self.diagnostics
        ):
            raise ValueError("readiness diagnostics must be a tuple of strings")

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "backend_id": self.backend_id,
            "status": self.status.value,
            "reason": self.reason,
            "diagnostics": list(self.diagnostics),
        }


@dataclass(frozen=True, slots=True)
class ExecutionSource:
    project_path: str
    revision: str
    exact: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_path", _text(self.project_path, "project_path"))
        revision = _text(self.revision, "revision")
        if self.exact and _GIT_COMMIT.fullmatch(revision) is None:
            raise ValueError("exact source revision must be 40 lowercase hex characters")
        object.__setattr__(self, "revision", revision)
        if not isinstance(self.exact, bool):
            raise ValueError("source exact must be a boolean")

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "project_path": self.project_path,
            "revision": self.revision,
            "exact": self.exact,
        }


@dataclass(frozen=True, slots=True)
class ExecutionProfile:
    profile_id: str
    backend_id: str
    image_id: str
    toolchain_id: str

    def __post_init__(self) -> None:
        for field in ("profile_id", "backend_id", "image_id", "toolchain_id"):
            object.__setattr__(self, field, _logical_id(getattr(self, field), field))

    def to_json_dict(self) -> dict[str, str]:
        return {
            "profile_id": self.profile_id,
            "backend_id": self.backend_id,
            "image_id": self.image_id,
            "toolchain_id": self.toolchain_id,
        }


@dataclass(frozen=True, slots=True)
class ExecutionRequest:
    request_id: str
    project_id: str
    verification_profile_id: str
    source: ExecutionSource
    profile: ExecutionProfile
    executable: str
    arguments: tuple[str, ...]
    timeout_ms: int
    evidence_limit_chars: int
    schema_version: int = EXECUTION_SCHEMA_VERSION
    contract: str = EXECUTION_REQUEST_CONTRACT

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", _logical_id(self.request_id, "request_id"))
        object.__setattr__(self, "project_id", _logical_id(self.project_id, "project_id"))
        object.__setattr__(
            self,
            "verification_profile_id",
            _logical_id(self.verification_profile_id, "verification_profile_id"),
        )
        object.__setattr__(self, "executable", _text(self.executable, "executable"))
        if not isinstance(self.arguments, tuple) or any(
            not isinstance(item, str) or not item for item in self.arguments
        ):
            raise ValueError("arguments must be a tuple of non-empty strings")
        if isinstance(self.timeout_ms, bool) or not 1 <= self.timeout_ms <= 3_600_000:
            raise ValueError("timeout_ms must be an integer from 1 to 3600000")
        if isinstance(self.evidence_limit_chars, bool) or not 1 <= self.evidence_limit_chars <= 500_000:
            raise ValueError("evidence_limit_chars must be an integer from 1 to 500000")
        if self.schema_version != EXECUTION_SCHEMA_VERSION or self.contract != EXECUTION_REQUEST_CONTRACT:
            raise ValueError("execution request identity is fixed")

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "contract": self.contract,
            "request_id": self.request_id,
            "project_id": self.project_id,
            "verification_profile_id": self.verification_profile_id,
            "source": self.source.to_json_dict(),
            "profile": self.profile.to_json_dict(),
            "executable": self.executable,
            "arguments": list(self.arguments),
            "timeout_ms": self.timeout_ms,
            "evidence_limit_chars": self.evidence_limit_chars,
        }


@dataclass(frozen=True, slots=True)
class ExecutionEvidence:
    stdout: str = ""
    stderr: str = ""
    diagnostics: tuple[str, ...] = ()
    truncated: bool = False
    receipt_path: str | None = None
    transferred_bytes: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.stdout, str) or not isinstance(self.stderr, str):
            raise ValueError("execution evidence output must be text")
        if not isinstance(self.diagnostics, tuple) or any(
            not isinstance(item, str) for item in self.diagnostics
        ):
            raise ValueError("execution evidence diagnostics must be a tuple of strings")
        if not isinstance(self.truncated, bool):
            raise ValueError("execution evidence truncated must be a boolean")
        if self.receipt_path is not None:
            object.__setattr__(self, "receipt_path", _text(self.receipt_path, "receipt_path"))
        if self.transferred_bytes is not None and (
            isinstance(self.transferred_bytes, bool) or self.transferred_bytes < 0
        ):
            raise ValueError("transferred_bytes must be non-negative or null")

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "stdout": self.stdout,
            "stderr": self.stderr,
            "diagnostics": list(self.diagnostics),
            "truncated": self.truncated,
            "receipt_path": self.receipt_path,
            "transferred_bytes": self.transferred_bytes,
        }


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    request_id: str
    backend_id: str
    status: str
    exit_code: int | None
    duration_ms: int
    source_revision: str
    image_id: str
    toolchain_id: str
    cleanup: CleanupDisposition
    evidence: ExecutionEvidence
    failure_classification: str
    lifecycle: tuple[ExecutionLifecycleState, ...] = ()
    schema_version: int = EXECUTION_SCHEMA_VERSION
    contract: str = EXECUTION_RESULT_CONTRACT

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", _logical_id(self.request_id, "request_id"))
        object.__setattr__(self, "backend_id", _logical_id(self.backend_id, "backend_id"))
        object.__setattr__(self, "source_revision", _text(self.source_revision, "source_revision"))
        object.__setattr__(self, "image_id", _logical_id(self.image_id, "image_id"))
        object.__setattr__(self, "toolchain_id", _logical_id(self.toolchain_id, "toolchain_id"))
        if self.status not in _SUPPORTED_STATUSES:
            raise ValueError("execution result status is unsupported")
        if self.failure_classification not in _SUPPORTED_FAILURES:
            raise ValueError("execution failure classification is unsupported")
        if isinstance(self.duration_ms, bool) or self.duration_ms < 0:
            raise ValueError("execution duration must not be negative")
        if self.exit_code is not None and isinstance(self.exit_code, bool):
            raise ValueError("execution exit_code must be an integer or null")
        if not isinstance(self.lifecycle, tuple) or any(
            not isinstance(item, ExecutionLifecycleState) for item in self.lifecycle
        ):
            raise ValueError("execution lifecycle must be a tuple of lifecycle states")
        if self.status == "passed":
            if self.exit_code != 0 or self.cleanup not in {
                CleanupDisposition.NOT_REQUIRED,
                CleanupDisposition.DESTROYED,
                CleanupDisposition.QUARANTINED,
            }:
                raise ValueError("passed execution requires exit code 0 and complete cleanup")
            if self.failure_classification != "none":
                raise ValueError("passed execution requires failure classification none")
        if self.schema_version != EXECUTION_SCHEMA_VERSION or self.contract != EXECUTION_RESULT_CONTRACT:
            raise ValueError("execution result identity is fixed")

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "contract": self.contract,
            "request_id": self.request_id,
            "backend_id": self.backend_id,
            "status": self.status,
            "exit_code": self.exit_code,
            "duration_ms": self.duration_ms,
            "source_revision": self.source_revision,
            "image_id": self.image_id,
            "toolchain_id": self.toolchain_id,
            "cleanup": self.cleanup.value,
            "failure_classification": self.failure_classification,
            "lifecycle": [state.value for state in self.lifecycle],
            "evidence": self.evidence.to_json_dict(),
        }


__all__ = [
    "CleanupDisposition",
    "EXECUTION_REQUEST_CONTRACT",
    "EXECUTION_RESULT_CONTRACT",
    "EXECUTION_SCHEMA_VERSION",
    "ExecutionEvidence",
    "ExecutionLifecycleState",
    "ExecutionProfile",
    "ExecutionReadiness",
    "ExecutionRequest",
    "ExecutionResult",
    "ExecutionSource",
    "ReadinessStatus",
]
