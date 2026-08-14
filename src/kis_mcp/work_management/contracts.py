from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePosixPath, PureWindowsPath
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


_RECORD_PREFIXES = {
    RecordType.IDEA: "IDEA",
    RecordType.TASK: "TASK",
    RecordType.SPECIFICATION_SLICE: "SPEC",
    RecordType.REVIEW_RUN: "REV",
    RecordType.FINDING: "FIND",
    RecordType.DECISION: "DEC",
    RecordType.ASSUMPTION: "ASM",
    RecordType.RISK: "RISK",
    RecordType.APPROVAL: "APP",
    RecordType.HOLD: "HOLD",
    RecordType.RESEARCH: "RES",
    RecordType.DEFECT: "BUG",
    RecordType.SECURITY_FINDING: "SEC",
}


class LifecycleState(StrEnum):
    INBOX = "inbox"
    TRIAGE = "triage"
    PROPOSED = "proposed"
    APPROVED = "approved"
    READY = "ready"
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


class Effort(StrEnum):
    TINY = "tiny"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class DeliveryStage(StrEnum):
    NONE = "none"
    CHANGE_CREATED = "change_created"
    IMPLEMENTING = "implementing"
    PR_OPEN = "pr_open"
    REVIEW = "review"
    CI_PENDING = "ci_pending"
    CI_FAILED = "ci_failed"
    CI_PASSED = "ci_passed"
    MERGED = "merged"
    DOCUMENTATION = "documentation"
    COMMISSIONING = "commissioning"
    COMPLETE = "complete"


class ChangeComplexity(StrEnum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class RiskTrigger(StrEnum):
    SECURITY = "security"
    SECRETS = "secrets"
    SENSITIVE_DATA = "sensitive_data"
    MONEY = "money"
    PERSISTENT_STATE = "persistent_state"
    MIGRATION = "migration"
    EXTERNAL_ACTION = "external_action"
    DEPLOYMENT = "deployment"
    DESTRUCTIVE = "destructive"
    PUBLIC_CONTRACT = "public_contract"
    ARCHITECTURE_BOUNDARY = "architecture_boundary"


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


class DocumentationMilestoneState(StrEnum):
    NOT_REQUIRED = "not_required"
    DOCUMENTATION_RECONCILIATION_DUE = "documentation_reconciliation_due"
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
    repository: str | None
    backend_binding: str
    display_name: str | None = None
    schema_version: int = PUBLIC_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PUBLIC_SCHEMA_VERSION:
            raise ValueError("managed project schema_version must be 1")
        object.__setattr__(self, "project_id", _project_id(self.project_id))
        local_root = _required_text(self.local_root, "local_root")
        windows_root = PureWindowsPath(local_root)
        posix_root = PurePosixPath(local_root)
        if not windows_root.is_absolute() and not posix_root.is_absolute():
            raise ValueError("local_root must be an absolute path")
        if ".." in windows_root.parts or ".." in posix_root.parts:
            raise ValueError("local_root must not contain parent traversal")
        object.__setattr__(self, "local_root", local_root)
        repository = _optional_text(self.repository, "repository")
        if repository is not None and any(char.isspace() for char in repository):
            raise ValueError("repository must not contain whitespace")
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
    effort: Effort = Effort.MEDIUM
    delivery_stage: DeliveryStage = DeliveryStage.NONE
    execution_owner: str | None = None
    claimed_at: str | None = None
    queue_rank: int | None = None
    complexity: ChangeComplexity | None = None
    risk_triggers: tuple[RiskTrigger, ...] = ()
    dependency_ids: tuple[str, ...] = ()
    approval_required: bool = False
    approval_complete: bool = False
    documentation_mode: DocumentationMode = DocumentationMode.REQUIRED
    documentation_impact: DocumentationImpact = DocumentationImpact.NOT_ASSESSED
    traceability_required: bool = False
    documentation_milestone: DocumentationMilestoneState = (
        DocumentationMilestoneState.NOT_REQUIRED
    )
    documentation_event_id: str | None = None
    documentation_rationale: str | None = None
    documentation_reviewer: str | None = None
    created_order: int = 0
    schema_version: int = PUBLIC_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PUBLIC_SCHEMA_VERSION:
            raise ValueError("work record schema_version must be 1")
        record_id = _record_id(self.record_id)
        object.__setattr__(self, "record_id", record_id)
        object.__setattr__(self, "project_id", _project_id(self.project_id))
        object.__setattr__(self, "title", _required_text(self.title, "title"))
        _enum(self.record_type, RecordType, "record_type")
        expected_prefix = f"{_RECORD_PREFIXES[self.record_type]}-"
        if not record_id.startswith(expected_prefix):
            raise ValueError("record_id prefix must match record_type")
        _enum(self.state, LifecycleState, "state")
        _enum(self.priority, Priority, "priority")
        _enum(self.effort, Effort, "effort")
        _enum(self.delivery_stage, DeliveryStage, "delivery_stage")
        execution_owner = _optional_text(self.execution_owner, "execution_owner")
        claimed_at = _optional_text(self.claimed_at, "claimed_at")
        if claimed_at is not None and execution_owner is None:
            raise ValueError("claimed_at requires execution_owner")
        object.__setattr__(self, "execution_owner", execution_owner)
        object.__setattr__(self, "claimed_at", claimed_at)
        if self.queue_rank is not None:
            if (
                isinstance(self.queue_rank, bool)
                or not isinstance(self.queue_rank, int)
                or self.queue_rank < 0
            ):
                raise ValueError("queue_rank must be a non-negative integer")
        if self.complexity is not None:
            _enum(self.complexity, ChangeComplexity, "complexity")
        triggers = tuple(self.risk_triggers)
        if any(not isinstance(item, RiskTrigger) for item in triggers):
            raise ValueError("risk_triggers must contain RiskTrigger values")
        if len(set(triggers)) != len(triggers):
            raise ValueError("risk_triggers must be unique")
        ordered_triggers = tuple(sorted(triggers, key=lambda item: item.value))
        object.__setattr__(self, "risk_triggers", ordered_triggers)
        _enum(self.documentation_mode, DocumentationMode, "documentation_mode")
        _enum(
            self.documentation_impact,
            DocumentationImpact,
            "documentation_impact",
        )
        _enum(
            self.documentation_milestone,
            DocumentationMilestoneState,
            "documentation_milestone",
        )
        if not isinstance(self.traceability_required, bool):
            raise ValueError("traceability_required must be a boolean")
        documentation_event_id = _optional_text(
            self.documentation_event_id,
            "documentation_event_id",
        )
        object.__setattr__(
            self,
            "documentation_event_id",
            documentation_event_id,
        )
        if (
            self.documentation_milestone is DocumentationMilestoneState.NOT_REQUIRED
            and documentation_event_id is not None
        ):
            raise ValueError(
                "documentation_event_id requires a documentation milestone"
            )
        if (
            self.documentation_milestone is not DocumentationMilestoneState.NOT_REQUIRED
            and documentation_event_id is None
        ):
            raise ValueError(
                "documentation_event_id is required for a documentation milestone"
            )
        if not isinstance(self.approval_required, bool):
            raise ValueError("approval_required must be a boolean")
        if not isinstance(self.approval_complete, bool):
            raise ValueError("approval_complete must be a boolean")
        if isinstance(self.created_order, bool) or not isinstance(
            self.created_order, int
        ):
            raise ValueError("created_order must be a non-negative integer")
        if self.created_order < 0:
            raise ValueError("created_order must be a non-negative integer")
        dependencies = tuple(
            sorted(_record_id(item, "dependency_id") for item in self.dependency_ids)
        )
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
            "effort": self.effort.value,
            "delivery_stage": self.delivery_stage.value,
            "execution_owner": self.execution_owner,
            "claimed_at": self.claimed_at,
            "queue_rank": self.queue_rank,
            "complexity": self.complexity.value
            if self.complexity is not None
            else None,
            "risk_triggers": [item.value for item in self.risk_triggers],
            "dependency_ids": list(self.dependency_ids),
            "approval_required": self.approval_required,
            "approval_complete": self.approval_complete,
            "documentation_mode": self.documentation_mode.value,
            "documentation_impact": self.documentation_impact.value,
            "traceability_required": self.traceability_required,
            "documentation_milestone": self.documentation_milestone.value,
            "documentation_event_id": self.documentation_event_id,
            "documentation_rationale": self.documentation_rationale,
            "documentation_reviewer": self.documentation_reviewer,
            "created_order": self.created_order,
        }
