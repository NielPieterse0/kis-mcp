from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ...work_management import (
    ChangeComplexity,
    CloseoutEvidence,
    DeliveryStage,
    DesiredProjection,
    DocumentationImpact,
    DocumentationMilestoneState,
    DocumentationMode,
    DocumentationReconciliationEvent,
    Effort,
    ImplementationTrace,
    LifecycleState,
    MergeEvidence,
    ObservedProjection,
    Priority,
    PullRequestEvidence,
    PullRequestState,
    RecordType,
    RiskTrigger,
    TraceabilityStage,
    VerificationEvidence,
    VerificationStatus,
    WorkRecord,
)


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return dict(value)


def _array(value: Any, label: str) -> list[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError(f"{label} must be an array")
    return list(value)


def _fields(value: Any) -> tuple[tuple[str, Any], ...]:
    document = _object(value, "fields")
    return tuple(sorted(document.items(), key=lambda item: item[0].casefold()))


def desired_projection_from_json(
    value: Any,
    *,
    default_project_id: str | None = None,
) -> DesiredProjection:
    document = _object(value, "desired projection")
    project_id = document.get("project_id", default_project_id)
    return DesiredProjection(
        project_id=project_id,
        record_id=document["record_id"],
        fields=_fields(document.get("fields", {})),
        expected_revision=document.get("expected_revision"),
        source_repository=document.get("source_repository"),
        source_number=document.get("source_number"),
        source_kind=document.get("source_kind"),
    )


def observed_projection_from_json(
    value: Any,
    *,
    default_project_id: str | None = None,
) -> ObservedProjection:
    document = _object(value, "observed projection")
    project_id = document.get("project_id", default_project_id)
    return ObservedProjection(
        project_id=project_id,
        record_id=document["record_id"],
        fields=_fields(document.get("fields", {})),
        revision=document.get("revision"),
        accessible=document.get("accessible", True),
        external_id=document.get("external_id"),
    )


def work_record_from_json(value: Any) -> WorkRecord:
    document = _object(value, "work record")
    return WorkRecord(
        schema_version=document.get("schema_version", 1),
        record_id=document["record_id"],
        project_id=document["project_id"],
        title=document["title"],
        record_type=RecordType(document["record_type"]),
        state=LifecycleState(document.get("state", LifecycleState.INBOX.value)),
        priority=Priority(document.get("priority", Priority.MEDIUM.value)),
        effort=Effort(document.get("effort", Effort.MEDIUM.value)),
        delivery_stage=DeliveryStage(
            document.get("delivery_stage", DeliveryStage.NONE.value)
        ),
        execution_owner=document.get("execution_owner"),
        claimed_at=document.get("claimed_at"),
        queue_rank=document.get("queue_rank"),
        complexity=(
            ChangeComplexity(document["complexity"])
            if document.get("complexity") is not None
            else None
        ),
        risk_triggers=tuple(
            RiskTrigger(value) for value in document.get("risk_triggers", ())
        ),
        dependency_ids=tuple(document.get("dependency_ids", ())),
        approval_required=document.get("approval_required", False),
        approval_complete=document.get("approval_complete", False),
        documentation_mode=DocumentationMode(
            document.get("documentation_mode", DocumentationMode.REQUIRED.value)
        ),
        documentation_impact=DocumentationImpact(
            document.get(
                "documentation_impact",
                DocumentationImpact.NOT_ASSESSED.value,
            )
        ),
        traceability_required=document.get("traceability_required", False),
        documentation_milestone=DocumentationMilestoneState(
            document.get(
                "documentation_milestone",
                DocumentationMilestoneState.NOT_REQUIRED.value,
            )
        ),
        documentation_event_id=document.get("documentation_event_id"),
        documentation_rationale=document.get("documentation_rationale"),
        documentation_reviewer=document.get("documentation_reviewer"),
        created_order=document.get("created_order", 0),
    )


def implementation_trace_from_json(value: Any) -> ImplementationTrace:
    document = _object(value, "implementation trace")
    pull_requests = tuple(
        PullRequestEvidence(
            schema_version=item.get("schema_version", 1),
            repository=item["repository"],
            number=item["number"],
            head_branch=item["head_branch"],
            head_revision=item["head_revision"],
            base_branch=item["base_branch"],
            state=PullRequestState(item["state"]),
        )
        for raw in _array(document.get("pull_requests", ()), "pull_requests")
        for item in (_object(raw, "pull request evidence"),)
    )
    verifications = tuple(
        VerificationEvidence(
            schema_version=item.get("schema_version", 1),
            evidence_id=item["evidence_id"],
            pull_request_number=item["pull_request_number"],
            revision=item["revision"],
            status=VerificationStatus(item["status"]),
            command=item["command"],
            source=item.get("source", "local"),
            reference=item.get("reference"),
        )
        for raw in _array(document.get("verifications", ()), "verifications")
        for item in (_object(raw, "verification evidence"),)
    )
    merges = tuple(
        MergeEvidence(
            schema_version=item.get("schema_version", 1),
            pull_request_number=item["pull_request_number"],
            merge_commit=item["merge_commit"],
            head_revision=item["head_revision"],
        )
        for raw in _array(document.get("merges", ()), "merges")
        for item in (_object(raw, "merge evidence"),)
    )
    closeout_document = document.get("closeout")
    closeout = None
    if closeout_document is not None:
        item = _object(closeout_document, "closeout evidence")
        closeout = CloseoutEvidence(
            schema_version=item.get("schema_version", 1),
            path=item["path"],
            revision=item["revision"],
        )
    documentation_events = tuple(
        DocumentationReconciliationEvent(
            schema_version=item.get("schema_version", 1),
            event_id=item["event_id"],
            project_id=item["project_id"],
            implementation_record_id=item.get(
                "implementation_record_id",
                item.get("specification_record_id"),
            ),
            specification_record_id=item.get("specification_record_id"),
            change_id=item["change_id"],
            pull_request_number=item["pull_request_number"],
            merge_commit=item["merge_commit"],
            documentation_task_id=item["documentation_task_id"],
            required_updates=tuple(item["required_updates"]),
            state=DocumentationMilestoneState(item["state"]),
            completion_revision=item.get("completion_revision"),
        )
        for raw in _array(
            document.get("documentation_events", ()),
            "documentation_events",
        )
        for item in (_object(raw, "documentation reconciliation event"),)
    )
    return ImplementationTrace(
        schema_version=document.get("schema_version", 1),
        project_id=document["project_id"],
        implementation_record_id=document.get(
            "implementation_record_id",
            document.get("specification_record_id"),
        ),
        specification_record_id=document.get("specification_record_id"),
        change_id=document["change_id"],
        branch=document.get("branch"),
        worktree=document.get("worktree"),
        pull_requests=pull_requests,
        verifications=verifications,
        merges=merges,
        closeout=closeout,
        documentation_events=documentation_events,
    )


def traceability_stage(value: str) -> TraceabilityStage:
    return TraceabilityStage(value)


__all__ = [
    "desired_projection_from_json",
    "implementation_trace_from_json",
    "observed_projection_from_json",
    "traceability_stage",
    "work_record_from_json",
]
