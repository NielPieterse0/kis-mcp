from __future__ import annotations

from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any, Protocol

from .change_inspection_contracts import InspectChangeRequest
from .impact_contracts import ImpactBudget, InspectImpactRequest, InspectImpactResponse

ANALYZE_CHANGE_SCHEMA_VERSION = 1
ANALYZE_CHANGE_TOOL = "analyze_change"
_SUPPORTED_STATUSES = {"added", "copied", "deleted", "modified", "renamed", "type_changed", "unmerged", "unknown"}
_SUPPORTED_SOURCES = {"working_tree", "staged", "commit", "range", "branch", "supplied"}


def _required(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _path(value: str) -> str:
    normalized = _required(value, "change path").replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    normalized = normalized.strip("/")
    if not normalized or normalized.startswith("../") or "/../" in normalized or ":" in normalized:
        raise ValueError("change path must be repository-relative")
    return normalized


def _json(value: Any) -> Any:
    if hasattr(value, "to_json_dict"):
        return value.to_json_dict()
    if isinstance(value, tuple):
        return [_json(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json(item) for key, item in value.items()}
    return value


@dataclass(frozen=True, slots=True)
class _Record:
    def to_json_dict(self) -> dict[str, Any]:
        return {field.name: _json(getattr(self, field.name)) for field in fields(self)}


@dataclass(frozen=True, slots=True)
class SuppliedChange(_Record):
    path: str
    status: str = "modified"
    previous_path: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", _path(self.path))
        normalized_status = _required(self.status, "change status").casefold().replace("-", "_")
        if normalized_status not in _SUPPORTED_STATUSES:
            raise ValueError("change status is unsupported")
        object.__setattr__(self, "status", normalized_status)
        if self.previous_path is not None:
            object.__setattr__(self, "previous_path", _path(self.previous_path))


@dataclass(frozen=True, slots=True)
class GitHubChangeContext(_Record):
    repository: str
    pull_number: int
    base_sha: str
    head_sha: str
    changes: tuple[SuppliedChange, ...] = ()

    def __post_init__(self) -> None:
        repository = _required(self.repository, "GitHub repository")
        if repository.count("/") != 1 or any(not part for part in repository.split("/")):
            raise ValueError("GitHub repository must use owner/name form")
        object.__setattr__(self, "repository", repository)
        if isinstance(self.pull_number, bool) or not isinstance(self.pull_number, int) or self.pull_number < 1:
            raise ValueError("GitHub pull_number must be a positive integer")
        for field_name, value, label in (
            ("base_sha", self.base_sha, "GitHub base_sha"),
            ("head_sha", self.head_sha, "GitHub head_sha"),
        ):
            normalized = _required(value, label).casefold()
            if len(normalized) != 40 or any(char not in "0123456789abcdef" for char in normalized):
                raise ValueError(f"{label} must be a 40-character hexadecimal SHA")
            object.__setattr__(self, field_name, normalized)
        object.__setattr__(self, "changes", _dedupe_changes(self.changes))


@dataclass(frozen=True, slots=True)
class AnalyzeChangeRequest(_Record):
    project: str
    budget: ImpactBudget
    source: str = "working_tree"
    commit_ref: str | None = None
    base_ref: str | None = None
    head_ref: str | None = None
    task_terms: tuple[str, ...] = ()
    supplied_changes: tuple[SuppliedChange, ...] = ()
    github_context: GitHubChangeContext | None = None
    planned_paths: tuple[str, ...] = ()
    planned_impact_fingerprint: str | None = None

    def __post_init__(self) -> None:
        _required(self.project, "analyze change project")
        source = _required(self.source, "analyze change source").casefold()
        if source not in _SUPPORTED_SOURCES:
            raise ValueError("analyze change source is unsupported")
        object.__setattr__(self, "source", source)
        if not isinstance(self.budget, ImpactBudget):
            raise ValueError("analyze change budget must be an ImpactBudget")
        terms = tuple(dict.fromkeys(term.strip().casefold() for term in self.task_terms if isinstance(term, str) and term.strip()))
        object.__setattr__(self, "task_terms", terms)
        object.__setattr__(self, "supplied_changes", _dedupe_changes(self.supplied_changes))
        planned_paths = tuple(dict.fromkeys(_path(item) for item in self.planned_paths))
        object.__setattr__(self, "planned_paths", planned_paths)
        fingerprint = self.planned_impact_fingerprint
        if fingerprint is not None:
            normalized_fingerprint = _required(fingerprint, "planned impact fingerprint").casefold()
            if len(normalized_fingerprint) != 64 or any(
                character not in "0123456789abcdef" for character in normalized_fingerprint
            ):
                raise ValueError("planned impact fingerprint must be 64 lowercase hexadecimal characters")
            if not planned_paths:
                raise ValueError("planned impact fingerprint requires planned_paths")
            object.__setattr__(self, "planned_impact_fingerprint", normalized_fingerprint)
        if source == "supplied" and not self.supplied_changes and not (self.github_context and self.github_context.changes):
            raise ValueError("supplied source requires supplied_changes or github_context changes")
        if source != "supplied" and self.supplied_changes:
            raise ValueError("supplied_changes are accepted only for supplied source")
        InspectChangeRequest(
            path=self.project,
            source="working_tree" if source == "supplied" else source,
            commit_ref=self.commit_ref,
            base_ref=self.base_ref,
            head_ref=self.head_ref,
        )


@dataclass(frozen=True, slots=True)
class NormalizedChange(_Record):
    source: str
    changed_paths: tuple[str, ...]
    supplied_changes: tuple[SuppliedChange, ...]
    github_context: GitHubChangeContext | None


@dataclass(frozen=True, slots=True)
class ReplacementCandidate(_Record):
    path: str
    status: str
    reason: str
    remaining_references: tuple[str, ...]

    def __post_init__(self) -> None:
        _path(self.path)
        if self.status not in {"deleted", "renamed"}:
            raise ValueError("replacement candidate status must be deleted or renamed")
        _required(self.reason, "replacement candidate reason")
        if not self.remaining_references:
            raise ValueError("replacement candidate requires remaining reference evidence")


@dataclass(frozen=True, slots=True)
class ChangeImpactReconciliation(_Record):
    planned_paths: tuple[str, ...]
    actual_paths: tuple[str, ...]
    unplanned_paths: tuple[str, ...]
    missing_paths: tuple[str, ...]
    evidence_stale: bool
    planned_impact_fingerprint: str | None = None


@dataclass(frozen=True, slots=True)
class AnalyzeChangeResponse:
    normalized_change: NormalizedChange
    change: Any | None
    impact: InspectImpactResponse
    replacement_candidates: tuple[ReplacementCandidate, ...] = ()
    reconciliation: ChangeImpactReconciliation | None = None
    schema_version: int = ANALYZE_CHANGE_SCHEMA_VERSION
    tool: str = ANALYZE_CHANGE_TOOL

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "tool": self.tool,
            "normalized_change": self.normalized_change.to_json_dict(),
            "change": None if self.change is None else self.change.to_json_dict(),
            "impact": self.impact.to_json_dict(),
            "replacement_candidates": _json(self.replacement_candidates),
            "reconciliation": None if self.reconciliation is None else self.reconciliation.to_json_dict(),
        }


class ChangeInspectionPort(Protocol):
    def inspect(self, request: InspectChangeRequest) -> Any: ...


class ImpactInspectionPort(Protocol):
    def inspect(self, request: InspectImpactRequest) -> InspectImpactResponse: ...


class AnalyzeChangeService:
    def __init__(
        self,
        *,
        change_service: ChangeInspectionPort,
        impact_service: ImpactInspectionPort,
        max_changes: int = 100,
        max_task_terms: int = 50,
    ) -> None:
        if isinstance(max_changes, bool) or not isinstance(max_changes, int) or max_changes < 1:
            raise ValueError("analyze_change max_changes must be a positive integer")
        if isinstance(max_task_terms, bool) or not isinstance(max_task_terms, int) or max_task_terms < 1:
            raise ValueError("analyze_change max_task_terms must be a positive integer")
        self._change_service = change_service
        self._impact_service = impact_service
        self._max_changes = max_changes
        self._max_task_terms = max_task_terms

    def analyze(self, request: AnalyzeChangeRequest) -> AnalyzeChangeResponse:
        if len(request.task_terms) > self._max_task_terms:
            raise ValueError(
                f"analyze_change task term limit is {self._max_task_terms}"
            )
        if request.source == "supplied":
            change = None
            supplied = _dedupe_changes(
                (
                    *request.supplied_changes,
                    *(request.github_context.changes if request.github_context else ()),
                )
            )
            if len(supplied) > self._max_changes:
                raise ValueError(
                    f"analyze_change supplied change limit is {self._max_changes}"
                )
            changed_paths = tuple(
                sorted(
                    (item.path for item in supplied),
                    key=lambda value: (value.casefold(), value),
                )
            )
        else:
            change_request = InspectChangeRequest(
                path=request.project,
                source=request.source,
                commit_ref=request.commit_ref,
                base_ref=request.base_ref,
                head_ref=request.head_ref,
            )
            change = self._change_service.inspect(change_request)
            supplied = ()
            changed_paths = tuple(dict.fromkeys(item.path for item in change.changed_files))
            if len(changed_paths) > self._max_changes:
                raise ValueError(
                    f"analyze_change changed path limit is {self._max_changes}"
                )
        if not changed_paths:
            raise ValueError("analyze_change requires at least one changed path")
        impact = self._impact_service.inspect(
            InspectImpactRequest(
                project=request.project,
                changed_paths=changed_paths,
                budget=request.budget,
                task_terms=request.task_terms,
            )
        )
        return AnalyzeChangeResponse(
            normalized_change=NormalizedChange(
                source=request.source,
                changed_paths=changed_paths,
                supplied_changes=supplied,
                github_context=request.github_context,
            ),
            change=change,
            impact=impact,
            replacement_candidates=_replacement_candidates(
                change=change,
                supplied=supplied,
                impact=impact,
            ),
            reconciliation=_reconcile_change(request, changed_paths),
        )


def _reconcile_change(
    request: AnalyzeChangeRequest,
    actual_paths: tuple[str, ...],
) -> ChangeImpactReconciliation | None:
    if not request.planned_paths:
        return None
    planned = request.planned_paths
    planned_set = set(planned)
    actual_set = set(actual_paths)
    unplanned = tuple(path for path in actual_paths if path not in planned_set)
    missing = tuple(path for path in planned if path not in actual_set)
    return ChangeImpactReconciliation(
        planned_paths=planned,
        actual_paths=actual_paths,
        unplanned_paths=unplanned,
        missing_paths=missing,
        evidence_stale=bool(unplanned or missing),
        planned_impact_fingerprint=request.planned_impact_fingerprint,
    )


def _replacement_candidates(
    *,
    change: Any | None,
    supplied: tuple[SuppliedChange, ...],
    impact: InspectImpactResponse,
) -> tuple[ReplacementCandidate, ...]:
    statuses: dict[str, str] = {}
    for item in supplied:
        if item.status == "renamed" and item.previous_path:
            statuses[item.previous_path] = "renamed"
        elif item.status == "deleted":
            statuses[item.path] = "deleted"
    if change is not None:
        for item in getattr(change, "changed_files", ()):
            staged_status = getattr(item, "staged_status", None)
            worktree_status = getattr(item, "worktree_status", None)
            if "renamed" in {staged_status, worktree_status}:
                previous_path = getattr(item, "previous_path", None)
                if previous_path:
                    statuses[str(previous_path)] = "renamed"
            elif "deleted" in {staged_status, worktree_status}:
                statuses[str(item.path)] = "deleted"

    results: list[ReplacementCandidate] = []
    for path, status in sorted(statuses.items(), key=lambda item: (item[0].casefold(), item[0])):
        stem = Path(path).stem.casefold()
        references: list[str] = []
        for item in impact.dependants:
            if item.kind != "import":
                continue
            target = item.target.casefold().replace("::", ".").rsplit(".", 1)[-1]
            if target == stem:
                references.append(f"{item.kind}:{item.path}:{item.source}->{item.target}")
        for item in impact.relationship_impacts:
            if item.target_path == path or item.source_path == path:
                other = item.source_path if item.target_path == path else item.target_path
                references.append(f"{item.kind}:{other}")
        unique = tuple(dict.fromkeys(references))
        if not unique:
            continue
        results.append(
            ReplacementCandidate(
                path=path,
                status=status,
                reason=(
                    "Deleted or renamed code retains deterministic dependant/reference evidence; "
                    "confirm replacement and consumers before treating it as stale."
                ),
                remaining_references=unique,
            )
        )
    return tuple(results)


def _dedupe_changes(changes: tuple[SuppliedChange, ...]) -> tuple[SuppliedChange, ...]:
    values: dict[tuple[str, str, str | None], SuppliedChange] = {}
    for item in changes:
        if not isinstance(item, SuppliedChange):
            raise ValueError("changes must contain SuppliedChange records")
        values.setdefault((item.path, item.status, item.previous_path), item)
    return tuple(values.values())


__all__ = [
    "AnalyzeChangeRequest",
    "AnalyzeChangeResponse",
    "AnalyzeChangeService",
    "ChangeImpactReconciliation",
    "GitHubChangeContext",
    "NormalizedChange",
    "ReplacementCandidate",
    "SuppliedChange",
]
