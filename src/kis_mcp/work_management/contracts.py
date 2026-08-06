from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

PUBLIC_SCHEMA_VERSION = 1
_PROJECT_ID = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
_RECORD_ID = re.compile(r"^[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-[0-9]+$")


class RecordType(StrEnum):
    IDEA = "idea"
    TASK = "task"
    SPECIFICATION_SLICE = "specification_slice"
    REVIEW_RUN = "review_run"
    FINDING = "finding"
    DECISION = "decision"
    ASSUMPTION = "assumption"
    RISK = "risk"
    APPROVAL = "approval"
    HOLD = "hold"
    RESEARCH = "research"
    DEFECT = "defect"
    SECURITY_FINDING = "security_finding"


class LifecycleState(StrEnum):
    INBOX = "inbox"
    TRIAGE = "triage"
    PROPOSED = "proposed"
    APPROVED = "approved"
    ACTIVE = "active"
    REVIEW = "review"
    VERIFICATION = "verification"
    DOCUMENTATION = "documentation"
    DONE = "done"
    BLOCKED = "blocked"
    ON_HOLD = "on_hold"
    DEFERRED = "deferred"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class Priority(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DocumentationMode(StrEnum):
    OFF = "off"
    ADVISORY = "advisory"
    REQUIRED = "required"


class DocumentationImpact(StrEnum):
    NOT_ASSESSED = "not_assessed"
    NONE = "none"
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    PRE_MERGE_COMPLETE = "pre_merge_complete"
    POST_MERGE_COMPLETE = "post_merge_complete"


def _required_text(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _project_id(value: str, label: str = "project_id") -> str:
    normalized = _required_text(value, label)
    if not _PROJECT_ID.fullmatch(normalized):
        raise ValueError(f"{label} must use lower-case kebab-case")
    return normalized


def _record_id(value: str, label: str = "record_id") -> str:
    normalized = _required_text(value, label)
    if not _RECORD_ID.fullmatch(normalized):
        raise ValueError(f"{label} must use an upper-case stable prefix and number")
    return normalized


def _enum(value: Any, enum_type: type[StrEnum], label: str) -> StrEnum:
    if not isinstance(value, enum_type):
        raise ValueError(f"{label} must be a {enum_type.__name__} value")
    return value


def _optional_text(value: str | None, label: str) -> str | None:
    if value is None:
        return None
    return _required_text(value, label)


@dataclass(frozen=True, slots=True)
class ManagedProject:
    project_id: str
    local_root: str
    repository: str
    backend_binding: str
    display_name: str | None = None
    schema_version: int = PUBLIC_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PUBLIC_SCHEMA_VERSION:
            raise ValueError("managed project schema_version must be 1")
        object.__setattr__(self, "project_id", _project_id(self.project_id))
        object.__setattr__(
            self, "local_root", _required_text(self.local_root, "local_root")
        )
        repository = _required_text(self.repository, "repository")
        if repository.count("/") != 1 or any(char.isspace() for char in repository):
            raise ValueError("repository must use owner/name form")
        object.__setattr__(self, "repository", repository)
        object.__setattr__(
            self,
            "backend_binding",
            _project_id(self.backend_binding, "backend_binding"),
        )
        object.__setattr__(
            self, "display_name", _optional_text(self.display_name, "display_name")
        )

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "project_id": self.project_id,
            "local_root": self.local_root,
            "repository": self.repository,
            "backend_binding": self.backend_binding,
            "display_name": self.display_name,
        }


@dataclass(frozen=True, slots=True)
class WorkRecord:
    record_id: str
    project_id: str
    title: str
    record_type: RecordType
    state: LifecycleState = LifecycleState.INBOX
    priority: Priority = Priority.MEDIUM
    dependency_ids: tuple[str, ...] = ()
    approval_required: bool = False
    approval_complete: bool = False
    documentation_mode: DocumentationMode = DocumentationMode.REQUIRED
    documentation_impact: DocumentationImpact = DocumentationImpact.NOT_ASSESSED
    documentation_rationale: str | None = None
    documentation_reviewer: str | None = None
    created_order: int = 0
    schema_version: int = PUBLIC_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PUBLIC_SCHEMA_VERSION:
            raise ValueError("work record schema_version must be 1")
        object.__setattr__(self, "record_id", _record_id(self.record_id))
        object.__setattr__(self, "project_id", _project_id(self.project_id))
        object.__setattr__(self, "title", _required_text(self.title, "title"))
        _enum(self.record_type, RecordType, "record_type")
        _enum(self.state, LifecycleState, "state")
        _enum(self.priority, Priority, "priority")
        _enum(self.documentation_mode, DocumentationMode, "documentation_mode")
        _enum(
            self.documentation_impact,
            DocumentationImpact,
            "documentation_impact",
        )
        if not isinstance(self.approval_required, bool):
            raise ValueError("approval_required must be a boolean")
        if not isinstance(self.approval_complete, bool):
            raise ValueError("approval_complete must be a boolean")
        if isinstance(self.created_order, bool) or not isinstance(self.created_order, int):
            raise ValueError("created_order must be a non-negative integer")
        if self.created_order < 0:
            raise ValueError("created_order must be a non-negative integer")
        dependencies = tuple(sorted(_record_id(item, "dependency_id") for item in self.dependency_ids))
        if len(set(dependencies)) != len(dependencies):
            raise ValueError("dependency_ids must be unique")
        if self.record_id in dependencies:
            raise ValueError("record cannot depend on itself")
        object.__setattr__(self, "dependency_ids", dependencies)
        object.__setattr__(
            self,
            "documentation_rationale",
            _optional_text(self.documentation_rationale, "documentation_rationale"),
        )
        object.__setattr__(
            self,
            "documentation_reviewer",
            _optional_text(self.documentation_reviewer, "documentation_reviewer"),
        )

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "record_id": self.record_id,
            "project_id": self.project_id,
            "title": self.title,
            "record_type": self.record_type.value,
            "state": self.state.value,
            "priority": self.priority.value,
            "dependency_ids": list(self.dependency_ids),
            "approval_required": self.approval_required,
            "approval_complete": self.approval_complete,
            "documentation_mode": self.documentation_mode.value,
            "documentation_impact": self.documentation_impact.value,
            "documentation_rationale": self.documentation_rationale,
            "documentation_reviewer": self.documentation_reviewer,
            "created_order": self.created_order,
        }
