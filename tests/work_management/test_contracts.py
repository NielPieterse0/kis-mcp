from __future__ import annotations

import pytest

from kis_mcp.work_management import (
    DocumentationImpact,
    DocumentationMode,
    LifecycleState,
    ManagedProject,
    Priority,
    RecordType,
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


def test_work_record_rejects_wrong_enum_types() -> None:
    with pytest.raises(ValueError, match="record_type"):
        WorkRecord(
            record_id="TASK-001",
            project_id="alpha-project",
            title="Invalid record",
            record_type="task",  # type: ignore[arg-type]
        )
