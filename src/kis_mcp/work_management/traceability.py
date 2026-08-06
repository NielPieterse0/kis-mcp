from __future__ import annotations

import re
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Any

from .contracts import (
    PUBLIC_SCHEMA_VERSION,
    DocumentationImpact,
    DocumentationMilestoneState,
    DocumentationMode,
    LifecycleState,
    WorkRecord,
)
from .lifecycle import transition_record

_PROJECT_ID = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
_RECORD_ID = re.compile(r"^[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-[0-9]+$")
_CHANGE_ID = re.compile(r"^[0-9]{3}-[a-z0-9]+(?:-[a-z0-9]+)*$")
_REVISION = re.compile(r"^[0-9a-fA-F]{7,64}$")


class PullRequestState(StrEnum):
    OPEN = "open"
    CLOSED = "closed"
    MERGED = "merged"


class VerificationStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class TraceabilityStage(StrEnum):
    ACTIVE = "active"
    REVIEW = "review"
    MERGE_READY = "merge_ready"
    MERGED = "merged"
    CLOSED = "closed"


class TraceabilityIssueKind(StrEnum):
    MISSING = "missing"
    STALE = "stale"
    DUPLICATED = "duplicated"
    CONTRADICTORY = "contradictory"


def _required_text(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _optional_text(value: str | None, label: str) -> str | None:
    if value is None:
        return None
    return _required_text(value, label)


def _positive_int(value: int, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return value


def _project_id(value: str, label: str = "project_id") -> str:
    normalized = _required_text(value, label)
    if _PROJECT_ID.fullmatch(normalized) is None:
        raise ValueError(f"{label} must use lower-case kebab-case")
    return normalized


def _record_id(value: str, label: str = "record_id") -> str:
    normalized = _required_text(value, label)
    if _RECORD_ID.fullmatch(normalized) is None:
        raise ValueError(f"{label} must use an upper-case stable prefix and number")
    return normalized


def _specification_record_id(value: str) -> str:
    normalized = _record_id(value, "specification_record_id")
    if not normalized.startswith("SPEC-"):
        raise ValueError("specification_record_id must use the SPEC prefix")
    return normalized


def _change_id(value: str) -> str:
    normalized = _required_text(value, "change_id")
    if _CHANGE_ID.fullmatch(normalized) is None:
        raise ValueError("change_id must use NNN-kebab-case")
    return normalized


def _revision(value: str, label: str = "revision") -> str:
    normalized = _required_text(value, label)
    if _REVISION.fullmatch(normalized) is None:
        raise ValueError(f"{label} must be a 7-64 character hexadecimal revision")
    return normalized.lower()


def _enum(value: Any, enum_type: type[StrEnum], label: str) -> StrEnum:
    if not isinstance(value, enum_type):
        raise ValueError(f"{label} must be a {enum_type.__name__} value")
    return value


def _texts(values: tuple[str, ...], label: str, *, required: bool = False) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise ValueError(f"{label} must be a tuple")
    normalized = tuple(_required_text(value, label) for value in values)
    if required and not normalized:
        raise ValueError(f"{label} must contain at least one value")
    if len(set(normalized)) != len(normalized):
        raise ValueError(f"{label} must contain unique values")
    return normalized


@dataclass(frozen=True, slots=True)
class PullRequestEvidence:
    repository: str
    number: int
    head_branch: str
    head_revision: str
    base_branch: str
    state: PullRequestState
    schema_version: int = PUBLIC_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PUBLIC_SCHEMA_VERSION:
            raise ValueError("pull request evidence schema_version must be 1")
        repository = _required_text(self.repository, "repository")
        if any(character.isspace() for character in repository):
            raise ValueError("repository must not contain whitespace")
        object.__setattr__(self, "repository", repository)
        object.__setattr__(self, "number", _positive_int(self.number, "number"))
        object.__setattr__(self, "head_branch", _required_text(self.head_branch, "head_branch"))
        object.__setattr__(self, "head_revision", _revision(self.head_revision, "head_revision"))
        object.__setattr__(self, "base_branch", _required_text(self.base_branch, "base_branch"))
        _enum(self.state, PullRequestState, "state")

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "repository": self.repository,
            "number": self.number,
            "head_branch": self.head_branch,
            "head_revision": self.head_revision,
            "base_branch": self.base_branch,
            "state": self.state.value,
        }


@dataclass(frozen=True, slots=True)
class VerificationEvidence:
    evidence_id: str
    pull_request_number: int
    revision: str
    status: VerificationStatus
    command: str
    source: str = "local"
    reference: str | None = None
    schema_version: int = PUBLIC_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PUBLIC_SCHEMA_VERSION:
            raise ValueError("verification evidence schema_version must be 1")
        object.__setattr__(self, "evidence_id", _required_text(self.evidence_id, "evidence_id"))
        object.__setattr__(
            self,
            "pull_request_number",
            _positive_int(self.pull_request_number, "pull_request_number"),
        )
        object.__setattr__(self, "revision", _revision(self.revision))
        _enum(self.status, VerificationStatus, "status")
        object.__setattr__(self, "command", _required_text(self.command, "command"))
        object.__setattr__(self, "source", _required_text(self.source, "source"))
        object.__setattr__(self, "reference", _optional_text(self.reference, "reference"))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "evidence_id": self.evidence_id,
            "pull_request_number": self.pull_request_number,
            "revision": self.revision,
            "status": self.status.value,
            "command": self.command,
            "source": self.source,
            "reference": self.reference,
        }


@dataclass(frozen=True, slots=True)
class MergeEvidence:
    pull_request_number: int
    merge_commit: str
    head_revision: str
    schema_version: int = PUBLIC_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PUBLIC_SCHEMA_VERSION:
            raise ValueError("merge evidence schema_version must be 1")
        object.__setattr__(
            self,
            "pull_request_number",
            _positive_int(self.pull_request_number, "pull_request_number"),
        )
        object.__setattr__(self, "merge_commit", _revision(self.merge_commit, "merge_commit"))
        object.__setattr__(self, "head_revision", _revision(self.head_revision, "head_revision"))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "pull_request_number": self.pull_request_number,
            "merge_commit": self.merge_commit,
            "head_revision": self.head_revision,
        }


@dataclass(frozen=True, slots=True)
class CloseoutEvidence:
    path: str
    revision: str
    schema_version: int = PUBLIC_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PUBLIC_SCHEMA_VERSION:
            raise ValueError("closeout evidence schema_version must be 1")
        path = _required_text(self.path, "path").replace("\\", "/")
        if path.startswith("/") or ".." in path.split("/"):
            raise ValueError("path must be repository-relative without parent traversal")
        object.__setattr__(self, "path", path)
        object.__setattr__(self, "revision", _revision(self.revision))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "path": self.path,
            "revision": self.revision,
        }


@dataclass(frozen=True, slots=True)
class DocumentationReconciliationEvent:
    event_id: str
    project_id: str
    specification_record_id: str
    change_id: str
    pull_request_number: int
    merge_commit: str
    documentation_task_id: str
    required_updates: tuple[str, ...]
    state: DocumentationMilestoneState
    completion_revision: str | None = None
    schema_version: int = PUBLIC_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PUBLIC_SCHEMA_VERSION:
            raise ValueError("documentation event schema_version must be 1")
        object.__setattr__(self, "event_id", _required_text(self.event_id, "event_id"))
        object.__setattr__(self, "project_id", _project_id(self.project_id))
        object.__setattr__(
            self,
            "specification_record_id",
            _specification_record_id(self.specification_record_id),
        )
        object.__setattr__(self, "change_id", _change_id(self.change_id))
        object.__setattr__(
            self,
            "pull_request_number",
            _positive_int(self.pull_request_number, "pull_request_number"),
        )
        object.__setattr__(self, "merge_commit", _revision(self.merge_commit, "merge_commit"))
        object.__setattr__(
            self,
            "documentation_task_id",
            _required_text(self.documentation_task_id, "documentation_task_id"),
        )
        object.__setattr__(
            self,
            "required_updates",
            _texts(self.required_updates, "required_updates", required=True),
        )
        _enum(self.state, DocumentationMilestoneState, "state")
        completion_revision = self.completion_revision
        if completion_revision is not None:
            completion_revision = _revision(completion_revision, "completion_revision")
        object.__setattr__(self, "completion_revision", completion_revision)
        if self.state is DocumentationMilestoneState.DOCUMENTATION_RECONCILIATION_DUE:
            if completion_revision is not None:
                raise ValueError("due documentation event must not have completion_revision")
        elif self.state is DocumentationMilestoneState.POST_MERGE_COMPLETE:
            if completion_revision is None:
                raise ValueError("completed documentation event requires completion_revision")
        else:
            raise ValueError("documentation event state must be due or post_merge_complete")

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "event_id": self.event_id,
            "project_id": self.project_id,
            "specification_record_id": self.specification_record_id,
            "change_id": self.change_id,
            "pull_request_number": self.pull_request_number,
            "merge_commit": self.merge_commit,
            "documentation_task_id": self.documentation_task_id,
            "required_updates": list(self.required_updates),
            "state": self.state.value,
            "completion_revision": self.completion_revision,
        }


@dataclass(frozen=True, slots=True)
class ImplementationTrace:
    project_id: str
    specification_record_id: str | None
    change_id: str
    branch: str | None
    worktree: str | None
    pull_requests: tuple[PullRequestEvidence, ...] = ()
    verifications: tuple[VerificationEvidence, ...] = ()
    merges: tuple[MergeEvidence, ...] = ()
    closeout: CloseoutEvidence | None = None
    documentation_events: tuple[DocumentationReconciliationEvent, ...] = ()
    schema_version: int = PUBLIC_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PUBLIC_SCHEMA_VERSION:
            raise ValueError("implementation trace schema_version must be 1")
        object.__setattr__(self, "project_id", _project_id(self.project_id))
        specification_record_id = self.specification_record_id
        if specification_record_id is not None:
            specification_record_id = _specification_record_id(
                specification_record_id
            )
        object.__setattr__(self, "specification_record_id", specification_record_id)
        object.__setattr__(self, "change_id", _change_id(self.change_id))
        object.__setattr__(self, "branch", _optional_text(self.branch, "branch"))
        worktree = _optional_text(self.worktree, "worktree")
        if worktree is not None:
            worktree = worktree.replace("\\", "/")
            if worktree.startswith("/") or ".." in worktree.split("/"):
                raise ValueError("worktree must be repository-relative")
        object.__setattr__(self, "worktree", worktree)
        if any(not isinstance(value, PullRequestEvidence) for value in self.pull_requests):
            raise ValueError("pull_requests must contain PullRequestEvidence values")
        if any(not isinstance(value, VerificationEvidence) for value in self.verifications):
            raise ValueError("verifications must contain VerificationEvidence values")
        if any(not isinstance(value, MergeEvidence) for value in self.merges):
            raise ValueError("merges must contain MergeEvidence values")
        if self.closeout is not None and not isinstance(self.closeout, CloseoutEvidence):
            raise ValueError("closeout must be CloseoutEvidence or None")
        if any(
            not isinstance(value, DocumentationReconciliationEvent)
            for value in self.documentation_events
        ):
            raise ValueError(
                "documentation_events must contain DocumentationReconciliationEvent values"
            )
        object.__setattr__(self, "pull_requests", tuple(self.pull_requests))
        object.__setattr__(self, "verifications", tuple(self.verifications))
        object.__setattr__(self, "merges", tuple(self.merges))
        object.__setattr__(self, "documentation_events", tuple(self.documentation_events))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "project_id": self.project_id,
            "specification_record_id": self.specification_record_id,
            "change_id": self.change_id,
            "branch": self.branch,
            "worktree": self.worktree,
            "pull_requests": [value.to_json_dict() for value in self.pull_requests],
            "verifications": [value.to_json_dict() for value in self.verifications],
            "merges": [value.to_json_dict() for value in self.merges],
            "closeout": self.closeout.to_json_dict() if self.closeout else None,
            "documentation_events": [
                value.to_json_dict() for value in self.documentation_events
            ],
        }


@dataclass(frozen=True, slots=True)
class TraceabilityIssue:
    kind: TraceabilityIssueKind
    code: str
    subject: str
    message: str

    def __post_init__(self) -> None:
        _enum(self.kind, TraceabilityIssueKind, "kind")
        object.__setattr__(self, "code", _required_text(self.code, "code"))
        object.__setattr__(
            self,
            "subject",
            _required_text(self.subject, "subject"),
        )
        object.__setattr__(
            self,
            "message",
            _required_text(self.message, "message"),
        )

    def to_json_dict(self) -> dict[str, str]:
        return {
            "kind": self.kind.value,
            "code": self.code,
            "subject": self.subject,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class TraceabilityReport:
    stage: TraceabilityStage
    valid: bool
    issues: tuple[TraceabilityIssue, ...]

    def __post_init__(self) -> None:
        _enum(self.stage, TraceabilityStage, "stage")
        if not isinstance(self.valid, bool):
            raise ValueError("valid must be a boolean")
        if any(not isinstance(issue, TraceabilityIssue) for issue in self.issues):
            raise ValueError("issues must contain TraceabilityIssue values")
        object.__setattr__(self, "issues", tuple(self.issues))
        if self.valid != (not self.issues):
            raise ValueError("valid must reflect whether issues are empty")

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage.value,
            "valid": self.valid,
            "issues": [issue.to_json_dict() for issue in self.issues],
        }


@dataclass(frozen=True, slots=True)
class MergeReadiness:
    ready: bool
    blocking_reasons: tuple[str, ...]
    advisories: tuple[str, ...]
    traceability: TraceabilityReport

    def __post_init__(self) -> None:
        if not isinstance(self.ready, bool):
            raise ValueError("ready must be a boolean")
        object.__setattr__(
            self,
            "blocking_reasons",
            _texts(self.blocking_reasons, "blocking_reasons"),
        )
        object.__setattr__(
            self,
            "advisories",
            _texts(self.advisories, "advisories"),
        )
        if not isinstance(self.traceability, TraceabilityReport):
            raise ValueError("traceability must be a TraceabilityReport")
        if self.ready != (not self.blocking_reasons):
            raise ValueError("ready must reflect whether blocking_reasons are empty")

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "blocking_reasons": list(self.blocking_reasons),
            "advisories": list(self.advisories),
            "traceability": self.traceability.to_json_dict(),
        }


def evaluate_traceability(
    trace: ImplementationTrace,
    stage: TraceabilityStage,
    pull_request_number: int | None = None,
) -> TraceabilityReport:
    if not isinstance(trace, ImplementationTrace):
        raise ValueError("trace must be an ImplementationTrace")
    if not isinstance(stage, TraceabilityStage):
        raise ValueError("stage must be a TraceabilityStage value")
    if pull_request_number is not None:
        pull_request_number = _positive_int(
            pull_request_number,
            "pull_request_number",
        )

    issues: list[TraceabilityIssue] = []

    def add(
        kind: TraceabilityIssueKind,
        code: str,
        subject: str,
        message: str,
    ) -> None:
        issues.append(
            TraceabilityIssue(
                kind=kind,
                code=code,
                subject=subject,
                message=message,
            )
        )

    if trace.specification_record_id is None:
        add(
            TraceabilityIssueKind.MISSING,
            "missing_specification_record",
            trace.change_id,
            "The change is not linked to a specification-slice record.",
        )
    expected_branch = f"change/{trace.change_id}"
    expected_worktree = f".work/worktrees/{trace.change_id}"
    if trace.branch is None:
        add(
            TraceabilityIssueKind.MISSING,
            "missing_branch",
            trace.change_id,
            "The change has no branch evidence.",
        )
    elif trace.branch != expected_branch:
        add(
            TraceabilityIssueKind.CONTRADICTORY,
            "branch_change_mismatch",
            trace.branch,
            f"Expected branch {expected_branch}.",
        )
    if trace.worktree is None:
        add(
            TraceabilityIssueKind.MISSING,
            "missing_worktree",
            trace.change_id,
            "The change has no worktree evidence.",
        )
    elif trace.worktree != expected_worktree:
        add(
            TraceabilityIssueKind.CONTRADICTORY,
            "worktree_change_mismatch",
            trace.worktree,
            f"Expected worktree {expected_worktree}.",
        )

    pull_requests_by_number: dict[int, PullRequestEvidence] = {}
    pull_request_counts: dict[int, int] = {}
    for pull_request in trace.pull_requests:
        pull_request_counts[pull_request.number] = (
            pull_request_counts.get(pull_request.number, 0) + 1
        )
        pull_requests_by_number.setdefault(pull_request.number, pull_request)
        if trace.branch is not None and pull_request.head_branch != trace.branch:
            add(
                TraceabilityIssueKind.CONTRADICTORY,
                "pull_request_branch_mismatch",
                f"pr:{pull_request.number}",
                "Pull-request head branch does not match the change branch.",
            )
    for number, count in pull_request_counts.items():
        if count > 1:
            add(
                TraceabilityIssueKind.DUPLICATED,
                "duplicate_pull_request",
                f"pr:{number}",
                "The same pull request is linked more than once.",
            )

    pull_requests_with_current_verification = {
        pull_request.number
        for pull_request in trace.pull_requests
        if any(
            verification.pull_request_number == pull_request.number
            and verification.revision == pull_request.head_revision
            for verification in trace.verifications
        )
    }
    verification_counts: dict[str, int] = {}
    verification_relationship_ids: dict[
        tuple[int, str, VerificationStatus, str, str, str | None],
        set[str],
    ] = {}
    for verification in trace.verifications:
        verification_counts[verification.evidence_id] = (
            verification_counts.get(verification.evidence_id, 0) + 1
        )
        relationship = (
            verification.pull_request_number,
            verification.revision,
            verification.status,
            verification.command,
            verification.source,
            verification.reference,
        )
        verification_relationship_ids.setdefault(relationship, set()).add(
            verification.evidence_id
        )
        pull_request = pull_requests_by_number.get(
            verification.pull_request_number
        )
        if pull_request is None:
            add(
                TraceabilityIssueKind.CONTRADICTORY,
                "orphan_verification",
                verification.evidence_id,
                "Verification refers to an unlinked pull request.",
            )
        elif (
            verification.revision != pull_request.head_revision
            and pull_request.number
            not in pull_requests_with_current_verification
        ):
            add(
                TraceabilityIssueKind.STALE,
                "verification_revision_stale",
                verification.evidence_id,
                "Verification does not target the current pull-request head.",
            )
    for evidence_id, count in verification_counts.items():
        if count > 1:
            add(
                TraceabilityIssueKind.DUPLICATED,
                "duplicate_verification",
                evidence_id,
                "The same verification evidence is linked more than once.",
            )
    for relationship, evidence_ids in verification_relationship_ids.items():
        if len(evidence_ids) > 1:
            pull_request_number, revision, *_ = relationship
            add(
                TraceabilityIssueKind.DUPLICATED,
                "duplicate_verification",
                f"pr:{pull_request_number}:{revision}",
                "Equivalent verification evidence has multiple identities.",
            )

    merge_counts: dict[int, int] = {}
    merges_by_pull_request: dict[int, list[MergeEvidence]] = {}
    for merge in trace.merges:
        merge_counts[merge.pull_request_number] = (
            merge_counts.get(merge.pull_request_number, 0) + 1
        )
        merges_by_pull_request.setdefault(merge.pull_request_number, []).append(
            merge
        )
        pull_request = pull_requests_by_number.get(merge.pull_request_number)
        if pull_request is None:
            add(
                TraceabilityIssueKind.CONTRADICTORY,
                "orphan_merge",
                f"pr:{merge.pull_request_number}",
                "Merge evidence refers to an unlinked pull request.",
            )
        else:
            if pull_request.state is not PullRequestState.MERGED:
                add(
                    TraceabilityIssueKind.CONTRADICTORY,
                    "merge_pull_request_state_mismatch",
                    f"pr:{merge.pull_request_number}",
                    "Merge evidence requires the pull request state to be merged.",
                )
            if merge.head_revision != pull_request.head_revision:
                add(
                    TraceabilityIssueKind.CONTRADICTORY,
                    "merge_head_revision_mismatch",
                    f"pr:{merge.pull_request_number}",
                    "Merge evidence does not match the pull-request head revision.",
                )
    for number, count in merge_counts.items():
        if count > 1:
            add(
                TraceabilityIssueKind.DUPLICATED,
                "duplicate_merge",
                f"pr:{number}",
                "The pull request has multiple merge evidence records.",
            )

    event_counts: dict[str, int] = {}
    events_by_pull_request: dict[int, list[DocumentationReconciliationEvent]] = {}
    for event in trace.documentation_events:
        event_counts[event.event_id] = event_counts.get(event.event_id, 0) + 1
        events_by_pull_request.setdefault(event.pull_request_number, []).append(
            event
        )
        if (
            event.project_id != trace.project_id
            or event.specification_record_id != trace.specification_record_id
            or event.change_id != trace.change_id
        ):
            add(
                TraceabilityIssueKind.CONTRADICTORY,
                "documentation_event_identity_mismatch",
                event.event_id,
                "Documentation event identity does not match the trace.",
            )
        merges = merges_by_pull_request.get(event.pull_request_number, [])
        if not merges:
            add(
                TraceabilityIssueKind.CONTRADICTORY,
                "orphan_documentation_event",
                event.event_id,
                "Documentation event has no matching merge evidence.",
            )
        elif all(merge.merge_commit != event.merge_commit for merge in merges):
            add(
                TraceabilityIssueKind.CONTRADICTORY,
                "documentation_merge_mismatch",
                event.event_id,
                "Documentation event merge commit does not match merge evidence.",
            )
    for event_id, count in event_counts.items():
        if count > 1:
            add(
                TraceabilityIssueKind.DUPLICATED,
                "duplicate_documentation_event",
                event_id,
                "The same documentation event is linked more than once.",
            )

    if trace.closeout is not None:
        expected_closeout_path = (
            f".work/changes/{trace.change_id}/closeout.md"
        )
        if trace.closeout.path != expected_closeout_path:
            add(
                TraceabilityIssueKind.CONTRADICTORY,
                "closeout_path_mismatch",
                trace.closeout.path,
                f"Expected closeout path {expected_closeout_path}.",
            )
        if not trace.merges:
            add(
                TraceabilityIssueKind.CONTRADICTORY,
                "closeout_without_merge",
                trace.closeout.path,
                "Closeout evidence exists before any merge evidence.",
            )

    selected_pull_request = None
    if pull_request_number is not None:
        selected_pull_request = pull_requests_by_number.get(pull_request_number)
    elif trace.pull_requests:
        selected_pull_request = min(
            trace.pull_requests,
            key=lambda value: (value.number, value.repository),
        )

    if stage in {
        TraceabilityStage.REVIEW,
        TraceabilityStage.MERGE_READY,
        TraceabilityStage.MERGED,
        TraceabilityStage.CLOSED,
    } and selected_pull_request is None:
        subject = (
            f"pr:{pull_request_number}"
            if pull_request_number is not None
            else trace.change_id
        )
        add(
            TraceabilityIssueKind.MISSING,
            "missing_pull_request",
            subject,
            "The required pull-request evidence is missing.",
        )

    if (
        stage in {TraceabilityStage.REVIEW, TraceabilityStage.MERGE_READY}
        and selected_pull_request is not None
        and selected_pull_request.state is not PullRequestState.OPEN
    ):
        add(
            TraceabilityIssueKind.CONTRADICTORY,
            "pull_request_state_not_open",
            f"pr:{selected_pull_request.number}",
            "Review and merge-ready stages require an open pull request.",
        )

    if stage in {
        TraceabilityStage.MERGE_READY,
        TraceabilityStage.MERGED,
        TraceabilityStage.CLOSED,
    } and selected_pull_request is not None:
        passed_exact = any(
            verification.pull_request_number == selected_pull_request.number
            and verification.revision == selected_pull_request.head_revision
            and verification.status is VerificationStatus.PASSED
            for verification in trace.verifications
        )
        if not passed_exact:
            add(
                TraceabilityIssueKind.MISSING,
                "missing_passing_verification",
                f"pr:{selected_pull_request.number}",
                "No passing verification targets the exact pull-request head.",
            )

    if stage in {
        TraceabilityStage.MERGED,
        TraceabilityStage.CLOSED,
    } and selected_pull_request is not None:
        if not merges_by_pull_request.get(selected_pull_request.number):
            add(
                TraceabilityIssueKind.MISSING,
                "missing_merge",
                f"pr:{selected_pull_request.number}",
                "The pull request has no merge evidence.",
            )

    if stage is TraceabilityStage.CLOSED:
        if trace.closeout is None:
            add(
                TraceabilityIssueKind.MISSING,
                "missing_closeout",
                trace.change_id,
                "The change has no closeout evidence.",
            )
        for merge in trace.merges:
            events = events_by_pull_request.get(merge.pull_request_number, [])
            matching_events = [
                event
                for event in events
                if event.merge_commit == merge.merge_commit
            ]
            if not matching_events:
                add(
                    TraceabilityIssueKind.MISSING,
                    "missing_documentation_event",
                    f"pr:{merge.pull_request_number}",
                    "The merge has no documentation reconciliation event.",
                )
            elif not any(
                event.state is DocumentationMilestoneState.POST_MERGE_COMPLETE
                for event in matching_events
            ):
                add(
                    TraceabilityIssueKind.MISSING,
                    "documentation_reconciliation_incomplete",
                    f"pr:{merge.pull_request_number}",
                    "Post-merge documentation reconciliation is incomplete.",
                )

    ordered = tuple(
        sorted(
            issues,
            key=lambda issue: (
                issue.kind.value,
                issue.code,
                issue.subject,
                issue.message,
            ),
        )
    )
    return TraceabilityReport(stage=stage, valid=not ordered, issues=ordered)


def evaluate_merge_readiness(
    record: WorkRecord,
    trace: ImplementationTrace,
    pull_request_number: int,
) -> MergeReadiness:
    if not isinstance(record, WorkRecord):
        raise ValueError("record must be a WorkRecord")
    if not isinstance(trace, ImplementationTrace):
        raise ValueError("trace must be an ImplementationTrace")
    pull_request_number = _positive_int(
        pull_request_number,
        "pull_request_number",
    )
    report = evaluate_traceability(
        trace,
        TraceabilityStage.MERGE_READY,
        pull_request_number,
    )
    blocking = {f"traceability:{issue.code}" for issue in report.issues}
    advisories: set[str] = set()

    if record.project_id != trace.project_id:
        blocking.add("record_project_mismatch")
    if record.record_id != trace.specification_record_id:
        blocking.add("record_specification_mismatch")

    documentation_ready = (
        record.documentation_impact is DocumentationImpact.PRE_MERGE_COMPLETE
        or (
            record.documentation_impact is DocumentationImpact.NONE
            and record.documentation_rationale is not None
            and record.documentation_reviewer is not None
        )
    )
    if record.documentation_mode is DocumentationMode.REQUIRED:
        if not documentation_ready:
            blocking.add("documentation_pre_merge_incomplete")
    elif record.documentation_mode is DocumentationMode.ADVISORY:
        if not documentation_ready:
            advisories.add("documentation_pre_merge_advisory_incomplete")

    blocking_reasons = tuple(sorted(blocking))
    advisory_reasons = tuple(sorted(advisories))
    return MergeReadiness(
        ready=not blocking_reasons,
        blocking_reasons=blocking_reasons,
        advisories=advisory_reasons,
        traceability=report,
    )


def create_documentation_reconciliation_due(
    trace: ImplementationTrace,
    pull_request_number: int,
    documentation_task_id: str,
    required_updates: tuple[str, ...],
) -> DocumentationReconciliationEvent:
    if not isinstance(trace, ImplementationTrace):
        raise ValueError("trace must be an ImplementationTrace")
    pull_request_number = _positive_int(
        pull_request_number,
        "pull_request_number",
    )
    if trace.specification_record_id is None:
        raise ValueError("specification record evidence is required")
    merges = [
        merge
        for merge in trace.merges
        if merge.pull_request_number == pull_request_number
    ]
    if len(merges) != 1:
        raise ValueError("exactly one merge evidence record is required")
    pull_requests = [
        pull_request
        for pull_request in trace.pull_requests
        if pull_request.number == pull_request_number
    ]
    if len(pull_requests) != 1:
        raise ValueError("exactly one pull request evidence record is required")
    merge = merges[0]
    pull_request = pull_requests[0]
    if pull_request.state is not PullRequestState.MERGED:
        raise ValueError("pull request must be merged before documentation is due")
    if merge.head_revision != pull_request.head_revision:
        raise ValueError("merge evidence does not match pull request head")
    return DocumentationReconciliationEvent(
        event_id=f"doc-{trace.change_id}-pr-{pull_request_number}",
        project_id=trace.project_id,
        specification_record_id=trace.specification_record_id,
        change_id=trace.change_id,
        pull_request_number=pull_request_number,
        merge_commit=merge.merge_commit,
        documentation_task_id=documentation_task_id,
        required_updates=required_updates,
        state=DocumentationMilestoneState.DOCUMENTATION_RECONCILIATION_DUE,
    )


def complete_documentation_reconciliation(
    event: DocumentationReconciliationEvent,
    completion_revision: str,
) -> DocumentationReconciliationEvent:
    if not isinstance(event, DocumentationReconciliationEvent):
        raise ValueError("event must be a DocumentationReconciliationEvent")
    if (
        event.state
        is not DocumentationMilestoneState.DOCUMENTATION_RECONCILIATION_DUE
    ):
        raise ValueError("only a due documentation event can be completed")
    return replace(
        event,
        state=DocumentationMilestoneState.POST_MERGE_COMPLETE,
        completion_revision=_revision(
            completion_revision,
            "completion_revision",
        ),
    )


def apply_documentation_reconciliation_event(
    record: WorkRecord,
    event: DocumentationReconciliationEvent,
) -> WorkRecord:
    if not isinstance(record, WorkRecord):
        raise ValueError("record must be a WorkRecord")
    if not isinstance(event, DocumentationReconciliationEvent):
        raise ValueError("event must be a DocumentationReconciliationEvent")
    if (
        record.project_id != event.project_id
        or record.record_id != event.specification_record_id
    ):
        raise ValueError("documentation event identity does not match record")
    if (
        record.documentation_event_id is not None
        and record.documentation_event_id != event.event_id
    ):
        raise ValueError("documentation event identity does not match record")

    if (
        event.state
        is DocumentationMilestoneState.DOCUMENTATION_RECONCILIATION_DUE
    ):
        if record.state is LifecycleState.VERIFICATION:
            record = transition_record(record, LifecycleState.DOCUMENTATION)
        elif record.state is not LifecycleState.DOCUMENTATION:
            raise ValueError(
                "due documentation event requires verification or documentation state"
            )
        return replace(
            record,
            traceability_required=True,
            documentation_milestone=(
                DocumentationMilestoneState.DOCUMENTATION_RECONCILIATION_DUE
            ),
            documentation_event_id=event.event_id,
        )

    if event.state is DocumentationMilestoneState.POST_MERGE_COMPLETE:
        if record.state is not LifecycleState.DOCUMENTATION:
            raise ValueError(
                "completed documentation event requires documentation state"
            )
        return replace(
            record,
            traceability_required=True,
            documentation_impact=DocumentationImpact.POST_MERGE_COMPLETE,
            documentation_milestone=(
                DocumentationMilestoneState.POST_MERGE_COMPLETE
            ),
            documentation_event_id=event.event_id,
        )
    raise ValueError("unsupported documentation event state")


__all__ = [
    "CloseoutEvidence",
    "DocumentationReconciliationEvent",
    "ImplementationTrace",
    "MergeEvidence",
    "MergeReadiness",
    "PullRequestEvidence",
    "PullRequestState",
    "TraceabilityIssue",
    "TraceabilityIssueKind",
    "TraceabilityReport",
    "TraceabilityStage",
    "VerificationEvidence",
    "VerificationStatus",
    "apply_documentation_reconciliation_event",
    "complete_documentation_reconciliation",
    "create_documentation_reconciliation_due",
    "evaluate_merge_readiness",
    "evaluate_traceability",
]
