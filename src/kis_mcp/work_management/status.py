from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Mapping

from .contracts import (
    DocumentationMilestoneState,
    LifecycleState,
    RecordType,
    WorkRecord,
)
from .settings import WorkManagementSettings


@dataclass(frozen=True, slots=True)
class ProjectProgrammeStatus:
    project_id: str
    repository: str
    state_counts: tuple[tuple[LifecycleState, int], ...]
    blocker_ids: tuple[str, ...] = ()
    risk_ids: tuple[str, ...] = ()
    documentation_due_ids: tuple[str, ...] = ()
    traceability_gaps: tuple[str, ...] = ()
    provider_failure: str | None = None
    truncated: bool = False

    def __post_init__(self) -> None:
        if not self.project_id or not self.repository:
            raise ValueError("project status identity must be populated")
        if any(not isinstance(state, LifecycleState) for state, _count in self.state_counts):
            raise ValueError("state_counts must use LifecycleState values")
        if any(isinstance(count, bool) or count < 0 for _state, count in self.state_counts):
            raise ValueError("state counts must be non-negative integers")
        if not isinstance(self.truncated, bool):
            raise ValueError("truncated must be a boolean")
        object.__setattr__(self, "state_counts", tuple(sorted(self.state_counts, key=lambda item: item[0].value)))
        object.__setattr__(self, "blocker_ids", tuple(sorted(self.blocker_ids)))
        object.__setattr__(self, "risk_ids", tuple(sorted(self.risk_ids)))
        object.__setattr__(self, "documentation_due_ids", tuple(sorted(self.documentation_due_ids)))
        object.__setattr__(self, "traceability_gaps", tuple(sorted(self.traceability_gaps)))
        if self.provider_failure is not None and not self.provider_failure.strip():
            raise ValueError("provider_failure must be non-empty when supplied")

    @property
    def total_records(self) -> int:
        return sum(count for _state, count in self.state_counts)

    def state_count(self, state: LifecycleState) -> int:
        return dict(self.state_counts).get(state, 0)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "repository": self.repository,
            "total_records": self.total_records,
            "state_counts": {state.value: count for state, count in self.state_counts},
            "blocker_ids": list(self.blocker_ids),
            "risk_ids": list(self.risk_ids),
            "documentation_due_ids": list(self.documentation_due_ids),
            "traceability_gaps": list(self.traceability_gaps),
            "provider_failure": self.provider_failure,
            "truncated": self.truncated,
        }


@dataclass(frozen=True, slots=True)
class PortfolioStatus:
    portfolio_id: str
    projects: tuple[ProjectProgrammeStatus, ...]

    def __post_init__(self) -> None:
        if not self.portfolio_id:
            raise ValueError("portfolio_id must be populated")
        project_ids = [item.project_id for item in self.projects]
        if len(set(project_ids)) != len(project_ids):
            raise ValueError("portfolio project IDs must be unique")
        object.__setattr__(self, "projects", tuple(sorted(self.projects, key=lambda item: item.project_id)))

    @property
    def total_records(self) -> int:
        return sum(item.total_records for item in self.projects)

    @property
    def provider_failure_count(self) -> int:
        return sum(item.provider_failure is not None for item in self.projects)

    def project(self, project_id: str) -> ProjectProgrammeStatus:
        for item in self.projects:
            if item.project_id == project_id:
                return item
        raise KeyError(project_id)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "portfolio_id": self.portfolio_id,
            "total_records": self.total_records,
            "provider_failure_count": self.provider_failure_count,
            "projects": [item.to_json_dict() for item in self.projects],
        }


def build_portfolio_status(
    settings: WorkManagementSettings,
    records: tuple[WorkRecord, ...],
    *,
    traceability_gaps: Mapping[str, tuple[str, ...]] | None = None,
    provider_failures: Mapping[str, str] | None = None,
    truncated_projects: tuple[str, ...] = (),
) -> PortfolioStatus:
    configured = {item.project_id: item for item in settings.managed_projects}
    records_by_project: dict[str, list[WorkRecord]] = {
        project_id: [] for project_id in configured
    }
    for record in records:
        if record.project_id not in configured:
            raise ValueError(
                f"work record references unconfigured project: {record.project_id}"
            )
        records_by_project[record.project_id].append(record)
    gaps = dict(traceability_gaps or {})
    failures = dict(provider_failures or {})
    unknown_metadata = (set(gaps) | set(failures) | set(truncated_projects)) - set(configured)
    if unknown_metadata:
        raise ValueError(
            "status metadata references unconfigured project: "
            + ", ".join(sorted(unknown_metadata))
        )
    statuses: list[ProjectProgrammeStatus] = []
    for project_id, project in sorted(configured.items()):
        project_records = records_by_project[project_id]
        counts = Counter(item.state for item in project_records)
        blocker_ids = tuple(
            item.record_id
            for item in project_records
            if item.state in {LifecycleState.BLOCKED, LifecycleState.ON_HOLD}
        )
        risk_ids = tuple(
            item.record_id
            for item in project_records
            if item.record_type in {RecordType.RISK, RecordType.SECURITY_FINDING}
        )
        documentation_due_ids = tuple(
            item.record_id
            for item in project_records
            if item.state is LifecycleState.DOCUMENTATION
            or item.documentation_milestone
            is DocumentationMilestoneState.DOCUMENTATION_RECONCILIATION_DUE
        )
        statuses.append(
            ProjectProgrammeStatus(
                project_id=project_id,
                repository=project.repository,
                state_counts=tuple(counts.items()),
                blocker_ids=blocker_ids,
                risk_ids=risk_ids,
                documentation_due_ids=documentation_due_ids,
                traceability_gaps=tuple(gaps.get(project_id, ())),
                provider_failure=failures.get(project_id),
                truncated=project_id in truncated_projects,
            )
        )
    return PortfolioStatus(portfolio_id=settings.portfolio_id, projects=tuple(statuses))


__all__ = [
    "PortfolioStatus",
    "ProjectProgrammeStatus",
    "build_portfolio_status",
]
