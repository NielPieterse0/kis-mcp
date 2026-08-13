from __future__ import annotations

import pytest

from kis_mcp.work_management import (
    ChangeComplexity,
    DocumentationImpact,
    DocumentationMilestoneState,
    DocumentationMode,
    LifecycleState,
    ManagedProject,
    Priority,
    RecordType,
    RiskTrigger,
    WorkRecord,
)


def test_managed_project_normalizes_stable_identity() -> None:
    project = ManagedProject(
        project_id="  alpha-project ",
        local_root=r"C:\Projects\alpha",
        repository=" owner/alpha ",
        backend_binding=" github-default ",
    )

    assert project.project_id == "alpha-project"
    assert project.repository == "owner/alpha"
    assert project.backend_binding == "github-default"
    assert project.to_json_dict()["local_root"] == r"C:\Projects\alpha"


def test_managed_project_rejects_invalid_identity() -> None:
    with pytest.raises(ValueError, match="project_id"):
        ManagedProject(
            project_id="Alpha Project",
            local_root=r"C:\Projects\alpha",
            repository="owner/alpha",
            backend_binding="github-default",
        )


def test_work_record_is_project_scoped_and_json_safe() -> None:
    record = WorkRecord(
        record_id="TASK-004",
        project_id="alpha-project",
        title="Implement bounded selection",
        record_type=RecordType.TASK,
        state=LifecycleState.APPROVED,
        priority=Priority.HIGH,
        dependency_ids=("TASK-002", "TASK-001"),
        approval_required=True,
        approval_complete=True,
        documentation_mode=DocumentationMode.REQUIRED,
        documentation_impact=DocumentationImpact.PLANNED,
        created_order=7,
    )

    assert record.dependency_ids == ("TASK-001", "TASK-002")
    assert record.to_json_dict()["record_type"] == "task"
    assert record.to_json_dict()["project_id"] == "alpha-project"


def test_work_record_serializes_two_axis_classification_canonically() -> None:
    record = WorkRecord(
        record_id="SPEC-117",
        project_id="kis-mcp",
        title="Two-axis governance",
        record_type=RecordType.SPECIFICATION_SLICE,
        complexity=ChangeComplexity.MEDIUM,
        risk_triggers=(RiskTrigger.PUBLIC_CONTRACT, RiskTrigger.EXTERNAL_ACTION),
    )

    payload = record.to_json_dict()

    assert payload["complexity"] == "medium"
    assert payload["risk_triggers"] == ["external_action", "public_contract"]


def test_work_record_rejects_duplicate_risk_triggers() -> None:
    with pytest.raises(ValueError, match="risk_triggers must be unique"):
        WorkRecord(
            record_id="SPEC-117",
            project_id="kis-mcp",
            title="Invalid classification",
            record_type=RecordType.SPECIFICATION_SLICE,
            risk_triggers=(RiskTrigger.SECRETS, RiskTrigger.SECRETS),
        )


def test_work_record_rejects_wrong_enum_types() -> None:
    with pytest.raises(ValueError, match="record_type"):
        WorkRecord(
            record_id="TASK-001",
            project_id="alpha-project",
            title="Invalid record",
            record_type="task",  # type: ignore[arg-type]
        )


def test_managed_project_accepts_provider_neutral_repository_identity() -> None:
    project = ManagedProject(
        project_id="nested-project",
        local_root=r"C:\Projects\nested",
        repository="group/subgroup/repository",
        backend_binding="future-backend",
    )

    assert project.repository == "group/subgroup/repository"


def test_managed_project_rejects_relative_local_root() -> None:
    with pytest.raises(ValueError, match="local_root"):
        ManagedProject(
            project_id="alpha-project",
            local_root="relative/project",
            repository="owner/alpha",
            backend_binding="github-default",
        )


def test_work_record_prefix_must_match_record_type() -> None:
    with pytest.raises(ValueError, match="record_id prefix"):
        WorkRecord(
            record_id="DEC-001",
            project_id="alpha-project",
            title="Mismatched record",
            record_type=RecordType.TASK,
        )


def test_work_record_serializes_traceability_documentation_milestone() -> None:
    record = WorkRecord(
        record_id="SPEC-053",
        project_id="kis-mcp",
        title="Trace implementation evidence",
        record_type=RecordType.SPECIFICATION_SLICE,
        traceability_required=True,
        documentation_milestone=(
            DocumentationMilestoneState.DOCUMENTATION_RECONCILIATION_DUE
        ),
        documentation_event_id="doc-053-work-management-traceability-pr-63",
    )

    payload = record.to_json_dict()

    assert payload["traceability_required"] is True
    assert (
        payload["documentation_milestone"]
        == "documentation_reconciliation_due"
    )
    assert (
        payload["documentation_event_id"]
        == "doc-053-work-management-traceability-pr-63"
    )


def test_documentation_milestone_requires_event_identity() -> None:
    with pytest.raises(ValueError, match="documentation_event_id"):
        WorkRecord(
            record_id="SPEC-053",
            project_id="kis-mcp",
            title="Trace implementation evidence",
            record_type=RecordType.SPECIFICATION_SLICE,
            traceability_required=True,
            documentation_milestone=(
                DocumentationMilestoneState.POST_MERGE_COMPLETE
            ),
        )
