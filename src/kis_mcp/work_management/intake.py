from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from .contracts import PUBLIC_SCHEMA_VERSION, LifecycleState, Priority, RecordType

_PROJECT_ID = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")


def _text(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _optional_text(value: str | None, label: str) -> str | None:
    if value is None:
        return None
    return _text(value, label)


def _project_id(value: str) -> str:
    normalized = _text(value, "project_id")
    if _PROJECT_ID.fullmatch(normalized) is None:
        raise ValueError("project_id must use lower-case kebab-case")
    return normalized


class MutationDisposition(StrEnum):
    CREATED = "created"
    UPDATED = "updated"
    CONFLICT = "conflict"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class CaptureWorkItem:
    project_id: str
    title: str
    idempotency_key: str
    note: str | None = None
    record_type: RecordType = RecordType.IDEA
    priority: Priority = Priority.MEDIUM
    module: str | None = None
    state: LifecycleState = LifecycleState.INBOX
    schema_version: int = PUBLIC_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PUBLIC_SCHEMA_VERSION:
            raise ValueError("capture command schema_version must be 1")
        object.__setattr__(self, "project_id", _project_id(self.project_id))
        object.__setattr__(self, "title", _text(self.title, "title"))
        object.__setattr__(self, "idempotency_key", _text(self.idempotency_key, "idempotency_key"))
        object.__setattr__(self, "note", _optional_text(self.note, "note"))
        object.__setattr__(self, "module", _optional_text(self.module, "module"))
        if not isinstance(self.record_type, RecordType):
            raise ValueError("record_type must be a RecordType value")
        if not isinstance(self.priority, Priority):
            raise ValueError("priority must be a Priority value")
        if not isinstance(self.state, LifecycleState):
            raise ValueError("state must be a LifecycleState value")

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "project_id": self.project_id,
            "title": self.title,
            "idempotency_key": self.idempotency_key,
            "note": self.note,
            "record_type": self.record_type.value,
            "priority": self.priority.value,
            "module": self.module,
            "state": self.state.value,
        }


@dataclass(frozen=True, slots=True)
class MutationResult:
    project_id: str
    idempotency_key: str
    disposition: MutationDisposition
    record_id: str | None
    message: str
    conflict_revision: str | None = None
    schema_version: int = PUBLIC_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PUBLIC_SCHEMA_VERSION:
            raise ValueError("mutation result schema_version must be 1")
        object.__setattr__(self, "project_id", _project_id(self.project_id))
        object.__setattr__(self, "idempotency_key", _text(self.idempotency_key, "idempotency_key"))
        if not isinstance(self.disposition, MutationDisposition):
            raise ValueError("disposition must be a MutationDisposition value")
        object.__setattr__(self, "record_id", _optional_text(self.record_id, "record_id"))
        object.__setattr__(self, "message", _text(self.message, "message"))
        object.__setattr__(self, "conflict_revision", _optional_text(self.conflict_revision, "conflict_revision"))
        if self.disposition is MutationDisposition.CONFLICT and self.conflict_revision is None:
            raise ValueError("conflict_revision is required for conflict results")

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "project_id": self.project_id,
            "idempotency_key": self.idempotency_key,
            "disposition": self.disposition.value,
            "record_id": self.record_id,
            "message": self.message,
            "conflict_revision": self.conflict_revision,
        }


@runtime_checkable
class IntakeBackend(Protocol):
    async def capture(self, command: CaptureWorkItem) -> MutationResult: ...


async def capture_work_item(
    backend: IntakeBackend,
    *,
    project_id: str,
    title: str,
    idempotency_key: str,
    note: str | None = None,
    record_type: RecordType = RecordType.IDEA,
    priority: Priority = Priority.MEDIUM,
    module: str | None = None,
    state: LifecycleState = LifecycleState.INBOX,
) -> MutationResult:
    if not isinstance(backend, IntakeBackend):
        raise ValueError("backend must implement IntakeBackend")
    command = CaptureWorkItem(
        project_id=project_id,
        title=title,
        idempotency_key=idempotency_key,
        note=note,
        record_type=record_type,
        priority=priority,
        module=module,
        state=state,
    )
    result = await backend.capture(command)
    if not isinstance(result, MutationResult):
        raise TypeError("intake backend returned an invalid result")
    if result.project_id != command.project_id or result.idempotency_key != command.idempotency_key:
        raise ValueError("intake backend returned mismatched identity")
    return result


__all__ = [
    "CaptureWorkItem",
    "IntakeBackend",
    "MutationDisposition",
    "MutationResult",
    "capture_work_item",
]
