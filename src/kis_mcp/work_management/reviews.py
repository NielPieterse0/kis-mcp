from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from typing import Any

from .contracts import (
    PUBLIC_SCHEMA_VERSION,
    LifecycleState,
    RecordType,
    WorkRecord,
)

_REVIEW_ID = re.compile(r"^REV-[0-9]+$")
_PROJECT_ID = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
_REVISION = re.compile(r"^[0-9a-fA-F]{7,64}$")


class ReviewType(StrEnum):
    CODE = "code"
    SECURITY = "security"
    REPOSITORY = "repository"
    ARCHITECTURE = "architecture"
    MODULARITY = "modularity"
    DOCUMENTATION = "documentation"
    COMPLIANCE = "compliance"


class ReviewStatus(StrEnum):
    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExtractionMode(StrEnum):
    REPORT_ONLY = "report_only"
    VALIDATED_FINDINGS = "validated_findings"
    FULL_GOVERNANCE = "full_governance"


class ObservationDisposition(StrEnum):
    REJECTED = "rejected"
    INFORMATIONAL = "informational"
    RECOMMENDATION = "recommendation"
    ASSUMPTION = "assumption"
    DECISION_REQUIRED = "decision_required"
    VALIDATED_FINDING = "validated_finding"
    RISK = "risk"
    DEFERRED_CANDIDATE = "deferred_candidate"


class ReviewArtifactKind(StrEnum):
    REQUEST = "request"
    REPORT = "report"
    RESULT = "result"
    COVERAGE = "coverage"
    SARIF = "sarif"
    CLOSEOUT = "closeout"


class FindingState(StrEnum):
    CANDIDATE = "candidate"
    VALIDATED = "validated"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    DEFERRED = "deferred"
    RISK_ACCEPTED = "risk_accepted"
    REMEDIATION = "remediation"
    VERIFICATION = "verification"
    CLOSED = "closed"


class FindingDisposition(StrEnum):
    VALIDATED = "validated"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    DEFERRED = "deferred"
    RISK_ACCEPTED = "risk_accepted"


def _required_text(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _optional_text(value: str | None, label: str) -> str | None:
    if value is None:
        return None
    return _required_text(value, label)


def _project_id(value: str) -> str:
    normalized = _required_text(value, "project_id")
    if _PROJECT_ID.fullmatch(normalized) is None:
        raise ValueError("project_id must use lower-case kebab-case")
    return normalized


def _review_id(value: str, label: str = "review_id") -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must use the REV-<number> identity")
    normalized = value.strip()
    if _REVIEW_ID.fullmatch(normalized) is None:
        raise ValueError(f"{label} must use the REV-<number> identity")
    return normalized


def _revision(value: str | None, label: str) -> str | None:
    if value is None:
        return None
    normalized = _required_text(value, label)
    if _REVISION.fullmatch(normalized) is None:
        raise ValueError(f"{label} must be a 7-64 character hexadecimal revision")
    return normalized.lower()


def _positive_int(value: int, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return value


def _enum(value: Any, enum_type: type[StrEnum], label: str) -> StrEnum:
    if not isinstance(value, enum_type):
        raise ValueError(f"{label} must be a {enum_type.__name__} value")
    return value


def _texts(
    values: tuple[str, ...],
    label: str,
    *,
    required: bool = False,
    sort: bool = False,
) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise ValueError(f"{label} must be a tuple")
    normalized = tuple(_required_text(value, label) for value in values)
    if required and not normalized:
        raise ValueError(f"{label} must contain at least one value")
    if len(set(normalized)) != len(normalized):
        raise ValueError(f"{label} must contain unique values")
    return tuple(sorted(normalized)) if sort else normalized


def _relative_path(value: str, label: str = "path") -> str:
    normalized = _required_text(value, label).replace("\\", "/")
    if normalized.startswith("/") or re.match(r"^[A-Za-z]:", normalized):
        raise ValueError(f"{label} must be repository-relative")
    parts = normalized.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        if ".." in parts:
            raise ValueError(f"{label} must not contain parent traversal")
        raise ValueError(f"{label} must be a normalized repository-relative path")
    return normalized


def _timestamp(value: str | None, label: str) -> str | None:
    if value is None:
        return None
    normalized = _required_text(value, label)
    try:
        datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{label} must be an ISO-8601 timestamp") from exc
    return normalized


@dataclass(frozen=True, slots=True)
class ReviewTarget:
    project_id: str
    repository: str
    commit: str | None = None
    range_start: str | None = None
    range_end: str | None = None
    pull_request: int | None = None
    branch: str | None = None
    paths: tuple[str, ...] = ()
    schema_version: int = PUBLIC_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PUBLIC_SCHEMA_VERSION:
            raise ValueError("review target schema_version must be 1")
        object.__setattr__(self, "project_id", _project_id(self.project_id))
        repository = _required_text(self.repository, "repository")
        if any(character.isspace() for character in repository):
            raise ValueError("repository must not contain whitespace")
        object.__setattr__(self, "repository", repository)
        object.__setattr__(self, "commit", _revision(self.commit, "commit"))
        range_start = _revision(self.range_start, "range_start")
        range_end = _revision(self.range_end, "range_end")
        if (range_start is None) != (range_end is None):
            raise ValueError("review target range requires range_start and range_end")
        object.__setattr__(self, "range_start", range_start)
        object.__setattr__(self, "range_end", range_end)
        pull_request = self.pull_request
        if pull_request is not None:
            pull_request = _positive_int(pull_request, "pull_request")
        object.__setattr__(self, "pull_request", pull_request)
        object.__setattr__(self, "branch", _optional_text(self.branch, "branch"))
        paths = tuple(_relative_path(value, "path") for value in self.paths)
        if len(set(paths)) != len(paths):
            raise ValueError("paths must contain unique values")
        object.__setattr__(self, "paths", tuple(sorted(paths)))
        selectors = (
            self.commit is not None,
            self.range_start is not None,
            self.pull_request is not None,
            self.branch is not None,
            bool(self.paths),
        )
        if not any(selectors):
            raise ValueError("review target requires at least one bounded selector")

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "project_id": self.project_id,
            "repository": self.repository,
            "commit": self.commit,
            "range_start": self.range_start,
            "range_end": self.range_end,
            "pull_request": self.pull_request,
            "branch": self.branch,
            "paths": list(self.paths),
        }


@dataclass(frozen=True, slots=True)
class ReviewBudget:
    max_evidence_chars: int
    max_observations: int
    max_findings: int
    schema_version: int = PUBLIC_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PUBLIC_SCHEMA_VERSION:
            raise ValueError("review budget schema_version must be 1")
        object.__setattr__(
            self,
            "max_evidence_chars",
            _positive_int(self.max_evidence_chars, "max_evidence_chars"),
        )
        object.__setattr__(
            self,
            "max_observations",
            _positive_int(self.max_observations, "max_observations"),
        )
        object.__setattr__(
            self,
            "max_findings",
            _positive_int(self.max_findings, "max_findings"),
        )

    def to_json_dict(self) -> dict[str, int]:
        return {
            "schema_version": self.schema_version,
            "max_evidence_chars": self.max_evidence_chars,
            "max_observations": self.max_observations,
            "max_findings": self.max_findings,
        }


@dataclass(frozen=True, slots=True)
class ReviewRequest:
    record: WorkRecord
    review_id: str
    review_type: ReviewType
    workflow_version: str
    target: ReviewTarget
    requester: str
    started_at: str
    status: ReviewStatus
    extraction_mode: ExtractionMode
    exclusions: tuple[str, ...]
    assumptions: tuple[str, ...]
    unknowns: tuple[str, ...]
    budget: ReviewBudget
    completed_at: str | None = None
    schema_version: int = PUBLIC_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PUBLIC_SCHEMA_VERSION:
            raise ValueError("review request schema_version must be 1")
        if not isinstance(self.record, WorkRecord):
            raise ValueError("record must be a WorkRecord")
        if self.record.record_type is not RecordType.REVIEW_RUN:
            raise ValueError("review record type must be review_run")
        review_id = _review_id(self.review_id)
        object.__setattr__(self, "review_id", review_id)
        _enum(self.review_type, ReviewType, "review_type")
        object.__setattr__(
            self,
            "workflow_version",
            _required_text(self.workflow_version, "workflow_version"),
        )
        if not isinstance(self.target, ReviewTarget):
            raise ValueError("target must be a ReviewTarget")
        if (
            self.record.record_id != review_id
            or self.record.project_id != self.target.project_id
        ):
            raise ValueError("review record identity must match review request")
        object.__setattr__(self, "requester", _required_text(self.requester, "requester"))
        object.__setattr__(self, "started_at", _timestamp(self.started_at, "started_at"))
        _enum(self.status, ReviewStatus, "status")
        _enum(self.extraction_mode, ExtractionMode, "extraction_mode")
        object.__setattr__(self, "exclusions", _texts(self.exclusions, "exclusions"))
        object.__setattr__(self, "assumptions", _texts(self.assumptions, "assumptions"))
        object.__setattr__(self, "unknowns", _texts(self.unknowns, "unknowns"))
        if not isinstance(self.budget, ReviewBudget):
            raise ValueError("budget must be a ReviewBudget")
        completed_at = _timestamp(self.completed_at, "completed_at")
        terminal = self.status in {
            ReviewStatus.COMPLETED,
            ReviewStatus.FAILED,
            ReviewStatus.CANCELLED,
        }
        if terminal and completed_at is None:
            raise ValueError("terminal review status requires completed_at")
        if not terminal and completed_at is not None:
            raise ValueError("non-terminal review status must not have completed_at")
        if completed_at is not None:
            started_value = datetime.fromisoformat(
                self.started_at.replace("Z", "+00:00")
            )
            completed_value = datetime.fromisoformat(
                completed_at.replace("Z", "+00:00")
            )
            if (started_value.tzinfo is None) != (completed_value.tzinfo is None):
                raise ValueError(
                    "started_at and completed_at must use matching timezone awareness"
                )
            if completed_value < started_value:
                raise ValueError("completed_at must not be before started_at")
        object.__setattr__(self, "completed_at", completed_at)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "record": self.record.to_json_dict(),
            "review_id": self.review_id,
            "review_type": self.review_type.value,
            "workflow_version": self.workflow_version,
            "target": self.target.to_json_dict(),
            "requester": self.requester,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "status": self.status.value,
            "extraction_mode": self.extraction_mode.value,
            "exclusions": list(self.exclusions),
            "assumptions": list(self.assumptions),
            "unknowns": list(self.unknowns),
            "budget": self.budget.to_json_dict(),
        }


@dataclass(frozen=True, slots=True)
class ReviewCoverage:
    complete: bool
    reviewed: tuple[str, ...]
    gaps: tuple[str, ...]
    truncated: bool

    def __post_init__(self) -> None:
        if not isinstance(self.complete, bool):
            raise ValueError("complete must be a boolean")
        if not isinstance(self.truncated, bool):
            raise ValueError("truncated must be a boolean")
        object.__setattr__(self, "reviewed", _texts(self.reviewed, "reviewed"))
        object.__setattr__(self, "gaps", _texts(self.gaps, "gaps"))
        if self.complete and (self.gaps or self.truncated):
            raise ValueError("complete coverage must not contain gaps or truncation")
        if not self.complete and not self.gaps and not self.truncated:
            raise ValueError("incomplete coverage requires gaps or truncation")

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "complete": self.complete,
            "reviewed": list(self.reviewed),
            "gaps": list(self.gaps),
            "truncated": self.truncated,
        }


@dataclass(frozen=True, slots=True)
class ReviewArtifact:
    kind: ReviewArtifactKind
    path: str
    media_type: str

    def __post_init__(self) -> None:
        _enum(self.kind, ReviewArtifactKind, "kind")
        object.__setattr__(self, "path", _relative_path(self.path))
        object.__setattr__(
            self,
            "media_type",
            _required_text(self.media_type, "media_type"),
        )

    def to_json_dict(self) -> dict[str, str]:
        return {
            "kind": self.kind.value,
            "path": self.path,
            "media_type": self.media_type,
        }


_ARTIFACT_FILENAMES = {
    ReviewArtifactKind.REQUEST: ("request.json", "application/json"),
    ReviewArtifactKind.REPORT: ("report.md", "text/markdown"),
    ReviewArtifactKind.RESULT: ("result.json", "application/json"),
    ReviewArtifactKind.COVERAGE: ("coverage.json", "application/json"),
    ReviewArtifactKind.SARIF: ("report.sarif", "application/sarif+json"),
    ReviewArtifactKind.CLOSEOUT: ("closeout.json", "application/json"),
}
_ARTIFACT_ORDER = {
    kind: index
    for index, kind in enumerate(
        (
            ReviewArtifactKind.REQUEST,
            ReviewArtifactKind.REPORT,
            ReviewArtifactKind.RESULT,
            ReviewArtifactKind.COVERAGE,
            ReviewArtifactKind.SARIF,
            ReviewArtifactKind.CLOSEOUT,
        )
    )
}


@dataclass(frozen=True, slots=True)
class ReviewEvidenceManifest:
    review_id: str
    artifacts: tuple[ReviewArtifact, ...]
    schema_version: int = PUBLIC_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PUBLIC_SCHEMA_VERSION:
            raise ValueError("review evidence manifest schema_version must be 1")
        review_id = _review_id(self.review_id)
        object.__setattr__(self, "review_id", review_id)
        if any(not isinstance(value, ReviewArtifact) for value in self.artifacts):
            raise ValueError("artifacts must contain ReviewArtifact values")
        artifacts = tuple(self.artifacts)
        kinds = [artifact.kind for artifact in artifacts]
        if len(set(kinds)) != len(kinds):
            raise ValueError("artifact kinds must be unique")
        required = {
            ReviewArtifactKind.REQUEST,
            ReviewArtifactKind.REPORT,
            ReviewArtifactKind.RESULT,
            ReviewArtifactKind.COVERAGE,
            ReviewArtifactKind.CLOSEOUT,
        }
        if not required.issubset(set(kinds)):
            raise ValueError("manifest is missing required review artifacts")
        root = f".work/reviews/{review_id}/"
        for artifact in artifacts:
            filename, media_type = _ARTIFACT_FILENAMES[artifact.kind]
            if artifact.path != f"{root}{filename}" or artifact.media_type != media_type:
                raise ValueError("artifact does not match canonical review evidence path")
        object.__setattr__(
            self,
            "artifacts",
            tuple(sorted(artifacts, key=lambda value: _ARTIFACT_ORDER[value.kind])),
        )

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "review_id": self.review_id,
            "artifacts": [artifact.to_json_dict() for artifact in self.artifacts],
        }


def create_review_evidence_manifest(
    review_id: str,
    *,
    include_sarif: bool = False,
) -> ReviewEvidenceManifest:
    normalized = _review_id(review_id)
    kinds = [
        ReviewArtifactKind.REQUEST,
        ReviewArtifactKind.REPORT,
        ReviewArtifactKind.RESULT,
        ReviewArtifactKind.COVERAGE,
    ]
    if include_sarif:
        kinds.append(ReviewArtifactKind.SARIF)
    kinds.append(ReviewArtifactKind.CLOSEOUT)
    artifacts = tuple(
        ReviewArtifact(
            kind=kind,
            path=f".work/reviews/{normalized}/{_ARTIFACT_FILENAMES[kind][0]}",
            media_type=_ARTIFACT_FILENAMES[kind][1],
        )
        for kind in kinds
    )
    return ReviewEvidenceManifest(review_id=normalized, artifacts=artifacts)


_ALLOWED_OBSERVATION_TYPES: dict[
    ObservationDisposition,
    frozenset[RecordType],
] = {
    ObservationDisposition.RECOMMENDATION: frozenset({RecordType.TASK}),
    ObservationDisposition.ASSUMPTION: frozenset({RecordType.ASSUMPTION}),
    ObservationDisposition.DECISION_REQUIRED: frozenset({RecordType.DECISION}),
    ObservationDisposition.VALIDATED_FINDING: frozenset(
        {RecordType.FINDING, RecordType.SECURITY_FINDING}
    ),
    ObservationDisposition.RISK: frozenset({RecordType.RISK}),
    ObservationDisposition.DEFERRED_CANDIDATE: frozenset(
        {RecordType.TASK, RecordType.HOLD}
    ),
}


@dataclass(frozen=True, slots=True)
class ReviewObservation:
    observation_id: str
    review_id: str
    project_id: str
    disposition: ObservationDisposition
    summary: str
    evidence: tuple[str, ...]
    location: str | None = None
    confidence: str | None = None
    severity: str | None = None
    record_type: RecordType | None = None
    security: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "observation_id",
            _required_text(self.observation_id, "observation_id"),
        )
        object.__setattr__(self, "review_id", _review_id(self.review_id))
        object.__setattr__(self, "project_id", _project_id(self.project_id))
        _enum(self.disposition, ObservationDisposition, "disposition")
        object.__setattr__(self, "summary", _required_text(self.summary, "summary"))
        object.__setattr__(
            self,
            "evidence",
            _texts(self.evidence, "evidence", required=True),
        )
        object.__setattr__(self, "location", _optional_text(self.location, "location"))
        object.__setattr__(
            self,
            "confidence",
            _optional_text(self.confidence, "confidence"),
        )
        object.__setattr__(self, "severity", _optional_text(self.severity, "severity"))
        if not isinstance(self.security, bool):
            raise ValueError("security must be a boolean")
        allowed = _ALLOWED_OBSERVATION_TYPES.get(self.disposition)
        record_type = self.record_type
        if record_type is not None:
            _enum(record_type, RecordType, "record_type")
            if allowed is None or record_type not in allowed:
                raise ValueError("record_type is incompatible with observation disposition")
        elif self.disposition is ObservationDisposition.DEFERRED_CANDIDATE:
            record_type = RecordType.TASK
        elif (
            allowed is not None
            and len(allowed) == 1
            and self.disposition is not ObservationDisposition.RECOMMENDATION
        ):
            record_type = next(iter(allowed))
        if self.disposition is ObservationDisposition.VALIDATED_FINDING:
            expected = (
                RecordType.SECURITY_FINDING if self.security else RecordType.FINDING
            )
            if record_type is None:
                record_type = expected
            elif record_type is not expected:
                raise ValueError("record_type is incompatible with security finding flag")
        elif self.security:
            raise ValueError("security flag requires validated finding disposition")
        object.__setattr__(self, "record_type", record_type)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "review_id": self.review_id,
            "project_id": self.project_id,
            "disposition": self.disposition.value,
            "summary": self.summary,
            "evidence": list(self.evidence),
            "location": self.location,
            "confidence": self.confidence,
            "severity": self.severity,
            "record_type": self.record_type.value if self.record_type else None,
            "security": self.security,
        }


@dataclass(frozen=True, slots=True)
class ReviewResult:
    request: ReviewRequest
    coverage: ReviewCoverage
    observations: tuple[ReviewObservation, ...]
    artifacts: ReviewEvidenceManifest
    diagnostics: tuple[str, ...] = ()
    schema_version: int = PUBLIC_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PUBLIC_SCHEMA_VERSION:
            raise ValueError("review result schema_version must be 1")
        if not isinstance(self.request, ReviewRequest):
            raise ValueError("request must be a ReviewRequest")
        if self.request.status not in {
            ReviewStatus.COMPLETED,
            ReviewStatus.FAILED,
            ReviewStatus.CANCELLED,
        }:
            raise ValueError("review result requires a terminal review request")
        if not isinstance(self.coverage, ReviewCoverage):
            raise ValueError("coverage must be ReviewCoverage")
        if any(not isinstance(item, ReviewObservation) for item in self.observations):
            raise ValueError("observations must contain ReviewObservation values")
        observations = tuple(
            sorted(
                self.observations,
                key=lambda item: (item.observation_id, item.disposition.value),
            )
        )
        identities = [item.observation_id for item in observations]
        if len(set(identities)) != len(identities):
            raise ValueError("observation identities must be unique")
        for item in observations:
            if (
                item.review_id != self.request.review_id
                or item.project_id != self.request.target.project_id
            ):
                raise ValueError("observation identity does not match review result")
        object.__setattr__(self, "observations", observations)
        if not isinstance(self.artifacts, ReviewEvidenceManifest):
            raise ValueError("artifacts must be a ReviewEvidenceManifest")
        if self.artifacts.review_id != self.request.review_id:
            raise ValueError("artifact identity does not match review result")
        diagnostics = _texts(self.diagnostics, "diagnostics")
        object.__setattr__(self, "diagnostics", diagnostics)
        if (
            self.request.status in {ReviewStatus.FAILED, ReviewStatus.CANCELLED}
            and not diagnostics
        ):
            raise ValueError("failed or cancelled review result requires diagnostics")
        if len(observations) > self.request.budget.max_observations:
            raise ValueError("observations exceed the review budget")
        evidence_chars = sum(
            len(value)
            for item in observations
            for value in item.evidence
        )
        if evidence_chars > self.request.budget.max_evidence_chars:
            raise ValueError("evidence exceeds the review budget")
        finding_count = sum(
            item.disposition is ObservationDisposition.VALIDATED_FINDING
            for item in observations
        )
        if finding_count > self.request.budget.max_findings:
            raise ValueError("findings exceed the review budget")

    def _ids(self, disposition: ObservationDisposition) -> list[str]:
        return [
            item.observation_id
            for item in self.observations
            if item.disposition is disposition
        ]

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "review_id": self.request.review_id,
            "review_type": self.request.review_type.value,
            "target": self.request.target.to_json_dict(),
            "status": self.request.status.value,
            "coverage": self.coverage.to_json_dict(),
            "observations": [item.to_json_dict() for item in self.observations],
            "findings": self._ids(ObservationDisposition.VALIDATED_FINDING),
            "decisions": self._ids(ObservationDisposition.DECISION_REQUIRED),
            "assumptions": self._ids(ObservationDisposition.ASSUMPTION),
            "risks": self._ids(ObservationDisposition.RISK),
            "artifacts": self.artifacts.to_json_dict(),
            "diagnostics": list(self.diagnostics),
        }


@dataclass(frozen=True, slots=True)
class ExtractedReviewRecord:
    project_id: str
    source_review_id: str
    source_observation_id: str
    deduplication_key: str
    record_type: RecordType
    title: str
    evidence: tuple[str, ...]
    location: str | None
    confidence: str | None
    severity: str | None
    state: LifecycleState

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_id", _project_id(self.project_id))
        object.__setattr__(
            self,
            "source_review_id",
            _review_id(self.source_review_id, "source_review_id"),
        )
        object.__setattr__(
            self,
            "source_observation_id",
            _required_text(self.source_observation_id, "source_observation_id"),
        )
        object.__setattr__(
            self,
            "deduplication_key",
            _required_text(self.deduplication_key, "deduplication_key"),
        )
        _enum(self.record_type, RecordType, "record_type")
        object.__setattr__(self, "title", _required_text(self.title, "title"))
        object.__setattr__(
            self,
            "evidence",
            _texts(self.evidence, "evidence", required=True),
        )
        object.__setattr__(self, "location", _optional_text(self.location, "location"))
        object.__setattr__(
            self,
            "confidence",
            _optional_text(self.confidence, "confidence"),
        )
        object.__setattr__(self, "severity", _optional_text(self.severity, "severity"))
        _enum(self.state, LifecycleState, "state")

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "source_review_id": self.source_review_id,
            "source_observation_id": self.source_observation_id,
            "deduplication_key": self.deduplication_key,
            "record_type": self.record_type.value,
            "title": self.title,
            "evidence": list(self.evidence),
            "location": self.location,
            "confidence": self.confidence,
            "severity": self.severity,
            "state": self.state.value,
        }


def extract_review_records(
    result: ReviewResult,
    mode: ExtractionMode,
) -> tuple[ExtractedReviewRecord, ...]:
    if not isinstance(result, ReviewResult):
        raise ValueError("result must be a ReviewResult")
    if not isinstance(mode, ExtractionMode):
        raise ValueError("mode must be an ExtractionMode value")
    if (
        mode is ExtractionMode.REPORT_ONLY
        or result.request.status is not ReviewStatus.COMPLETED
    ):
        return ()
    allowed = {ObservationDisposition.VALIDATED_FINDING}
    if mode is ExtractionMode.FULL_GOVERNANCE:
        allowed.update(
            {
                ObservationDisposition.RECOMMENDATION,
                ObservationDisposition.DECISION_REQUIRED,
                ObservationDisposition.ASSUMPTION,
                ObservationDisposition.RISK,
                ObservationDisposition.DEFERRED_CANDIDATE,
            }
        )
    extracted: list[ExtractedReviewRecord] = []
    for item in result.observations:
        if item.disposition not in allowed or item.record_type is None:
            continue
        if (
            item.record_type is RecordType.TASK
            and item.disposition is ObservationDisposition.DEFERRED_CANDIDATE
        ):
            state = LifecycleState.DEFERRED
        elif item.record_type is RecordType.HOLD:
            state = LifecycleState.ON_HOLD
        else:
            state = LifecycleState.TRIAGE
        extracted.append(
            ExtractedReviewRecord(
                project_id=item.project_id,
                source_review_id=item.review_id,
                source_observation_id=item.observation_id,
                deduplication_key=(
                    f"{item.review_id}:{item.observation_id}:{item.record_type.value}"
                ),
                record_type=item.record_type,
                title=item.summary,
                evidence=item.evidence,
                location=item.location,
                confidence=item.confidence,
                severity=item.severity,
                state=state,
            )
        )
    return tuple(
        sorted(
            extracted,
            key=lambda value: (value.source_observation_id, value.record_type.value),
        )
    )


@dataclass(frozen=True, slots=True)
class FindingDetails:
    source_review_id: str
    source_observation_id: str
    evidence: tuple[str, ...]
    location: str | None
    confidence: str
    severity: str
    validation_disposition: FindingDisposition | None = None
    remediation_record_id: str | None = None
    fix_pull_request: str | None = None
    follow_up_verification: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source_review_id",
            _review_id(self.source_review_id, "source_review_id"),
        )
        object.__setattr__(
            self,
            "source_observation_id",
            _required_text(self.source_observation_id, "source_observation_id"),
        )
        object.__setattr__(
            self,
            "evidence",
            _texts(self.evidence, "evidence", required=True),
        )
        object.__setattr__(self, "location", _optional_text(self.location, "location"))
        object.__setattr__(
            self,
            "confidence",
            _required_text(self.confidence, "confidence"),
        )
        object.__setattr__(self, "severity", _required_text(self.severity, "severity"))
        if self.validation_disposition is not None:
            _enum(
                self.validation_disposition,
                FindingDisposition,
                "validation_disposition",
            )
        for field_name in (
            "remediation_record_id",
            "fix_pull_request",
            "follow_up_verification",
        ):
            object.__setattr__(
                self,
                field_name,
                _optional_text(getattr(self, field_name), field_name),
            )

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "source_review_id": self.source_review_id,
            "source_observation_id": self.source_observation_id,
            "evidence": list(self.evidence),
            "location": self.location,
            "confidence": self.confidence,
            "severity": self.severity,
            "validation_disposition": (
                self.validation_disposition.value
                if self.validation_disposition is not None
                else None
            ),
            "remediation_record_id": self.remediation_record_id,
            "fix_pull_request": self.fix_pull_request,
            "follow_up_verification": self.follow_up_verification,
        }


@dataclass(frozen=True, slots=True)
class FindingRecord:
    record: WorkRecord
    details: FindingDetails
    state: FindingState = FindingState.CANDIDATE
    schema_version: int = PUBLIC_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PUBLIC_SCHEMA_VERSION:
            raise ValueError("finding record schema_version must be 1")
        if not isinstance(self.record, WorkRecord):
            raise ValueError("record must be a WorkRecord")
        if self.record.record_type not in {
            RecordType.FINDING,
            RecordType.SECURITY_FINDING,
        }:
            raise ValueError("finding record must use finding or security_finding type")
        if not isinstance(self.details, FindingDetails):
            raise ValueError("details must be FindingDetails")
        _enum(self.state, FindingState, "state")
        allowed_dispositions: dict[
            FindingState,
            frozenset[FindingDisposition | None],
        ] = {
            FindingState.CANDIDATE: frozenset({None}),
            FindingState.VALIDATED: frozenset({FindingDisposition.VALIDATED}),
            FindingState.ACCEPTED: frozenset({FindingDisposition.ACCEPTED}),
            FindingState.REJECTED: frozenset({FindingDisposition.REJECTED}),
            FindingState.DEFERRED: frozenset({FindingDisposition.DEFERRED}),
            FindingState.RISK_ACCEPTED: frozenset({FindingDisposition.RISK_ACCEPTED}),
            FindingState.REMEDIATION: frozenset({FindingDisposition.ACCEPTED}),
            FindingState.VERIFICATION: frozenset({FindingDisposition.ACCEPTED}),
            FindingState.CLOSED: frozenset(
                {
                    FindingDisposition.ACCEPTED,
                    FindingDisposition.REJECTED,
                    FindingDisposition.DEFERRED,
                    FindingDisposition.RISK_ACCEPTED,
                }
            ),
        }
        if self.details.validation_disposition not in allowed_dispositions[self.state]:
            raise ValueError("finding disposition contradicts finding state")
        if self.state in {FindingState.REMEDIATION, FindingState.VERIFICATION} and (
            self.details.remediation_record_id is None
        ):
            raise ValueError("remediation finding state requires remediation_record_id")
        if self.state is FindingState.VERIFICATION and (
            self.details.fix_pull_request is None
        ):
            raise ValueError("verification finding state requires fix_pull_request")
        if (
            self.state is FindingState.CLOSED
            and self.details.validation_disposition is FindingDisposition.ACCEPTED
        ):
            if self.details.remediation_record_id is None:
                raise ValueError("closed accepted finding requires remediation_record_id")
            if self.details.fix_pull_request is None:
                raise ValueError("closed accepted finding requires fix_pull_request")
            if self.details.follow_up_verification is None:
                raise ValueError("closed accepted finding requires follow_up_verification")

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "record": self.record.to_json_dict(),
            "details": self.details.to_json_dict(),
            "state": self.state.value,
        }


@dataclass(frozen=True, slots=True)
class FindingTransitionDecision:
    allowed: bool
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.allowed, bool):
            raise ValueError("allowed must be a boolean")
        object.__setattr__(self, "reasons", _texts(self.reasons, "reasons"))
        if self.allowed != (not self.reasons):
            raise ValueError("allowed must reflect whether reasons are empty")

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reasons": list(self.reasons),
        }


class FindingTransitionRejected(ValueError):
    def __init__(self, current: FindingState, target: FindingState, reasons: tuple[str, ...]) -> None:
        self.current = current
        self.target = target
        self.reasons = reasons
        super().__init__(
            f"finding transition {current.value}->{target.value} rejected: "
            + ", ".join(reasons)
        )


_FINDING_TRANSITIONS: dict[FindingState, frozenset[FindingState]] = {
    FindingState.CANDIDATE: frozenset({FindingState.VALIDATED}),
    FindingState.VALIDATED: frozenset(
        {
            FindingState.ACCEPTED,
            FindingState.REJECTED,
            FindingState.DEFERRED,
            FindingState.RISK_ACCEPTED,
        }
    ),
    FindingState.ACCEPTED: frozenset({FindingState.REMEDIATION}),
    FindingState.REJECTED: frozenset({FindingState.CLOSED}),
    FindingState.DEFERRED: frozenset({FindingState.CLOSED}),
    FindingState.RISK_ACCEPTED: frozenset({FindingState.CLOSED}),
    FindingState.REMEDIATION: frozenset({FindingState.VERIFICATION}),
    FindingState.VERIFICATION: frozenset({FindingState.CLOSED}),
    FindingState.CLOSED: frozenset(),
}


def evaluate_finding_transition(
    record: FindingRecord,
    target: FindingState,
) -> FindingTransitionDecision:
    if not isinstance(record, FindingRecord):
        raise ValueError("record must be a FindingRecord")
    if not isinstance(target, FindingState):
        raise ValueError("target must be a FindingState value")
    if target not in _FINDING_TRANSITIONS[record.state]:
        return FindingTransitionDecision(False, ("transition_not_declared",))
    reasons: list[str] = []
    if target is FindingState.REMEDIATION and (
        record.details.remediation_record_id is None
    ):
        reasons.append("remediation_record_required")
    if target is FindingState.VERIFICATION and (
        record.details.fix_pull_request is None
    ):
        reasons.append("fix_pull_request_required")
    if (
        target is FindingState.CLOSED
        and record.state is FindingState.VERIFICATION
        and record.details.follow_up_verification is None
    ):
        reasons.append("follow_up_verification_required")
    ordered = tuple(sorted(reasons))
    return FindingTransitionDecision(not ordered, ordered)


def transition_finding(record: FindingRecord, target: FindingState) -> FindingRecord:
    decision = evaluate_finding_transition(record, target)
    if not decision.allowed:
        raise FindingTransitionRejected(record.state, target, decision.reasons)
    disposition_by_target = {
        FindingState.VALIDATED: FindingDisposition.VALIDATED,
        FindingState.ACCEPTED: FindingDisposition.ACCEPTED,
        FindingState.REJECTED: FindingDisposition.REJECTED,
        FindingState.DEFERRED: FindingDisposition.DEFERRED,
        FindingState.RISK_ACCEPTED: FindingDisposition.RISK_ACCEPTED,
    }
    details = record.details
    disposition = disposition_by_target.get(target)
    if disposition is not None:
        details = replace(details, validation_disposition=disposition)
    return replace(record, details=details, state=target)


__all__ = [
    "ExtractionMode",
    "ExtractedReviewRecord",
    "FindingDetails",
    "FindingDisposition",
    "FindingRecord",
    "FindingState",
    "FindingTransitionDecision",
    "FindingTransitionRejected",
    "ObservationDisposition",
    "ReviewArtifact",
    "ReviewArtifactKind",
    "ReviewBudget",
    "ReviewCoverage",
    "ReviewEvidenceManifest",
    "ReviewObservation",
    "ReviewRequest",
    "ReviewResult",
    "ReviewStatus",
    "ReviewTarget",
    "ReviewType",
    "create_review_evidence_manifest",
    "evaluate_finding_transition",
    "extract_review_records",
    "transition_finding",
]
