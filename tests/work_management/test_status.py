from __future__ import annotations

from kis_mcp.work_management import (
    BackendBindingSettings,
    DocumentationMilestoneState,
    FeatureMode,
    GateMode,
    LifecycleState,
    ManagedProject,
    ProjectOwnerType,
    RecordType,
    WorkManagementSettings,
    WorkRecord,
    build_portfolio_status,
)
from kis_mcp.work_management.settings import EvidenceSettings


def settings() -> WorkManagementSettings:
    return WorkManagementSettings(
        enabled=True,
        portfolio_id="default",
        managed_projects=(
            ManagedProject(
                project_id="alpha-project",
                local_root="C:\\Projects\\alpha",
                repository="owner/alpha",
                backend_binding="github-alpha",
            ),
            ManagedProject(
                project_id="beta-project",
                local_root="C:\\Projects\\beta",
                repository="owner/beta",
                backend_binding="github-beta",
            ),
        ),
        backend_bindings=(
            BackendBindingSettings(
                binding_id="github-alpha",
                provider="github",
                owner="owner",
                owner_type=ProjectOwnerType.USER,
                project_number=1,
            ),
            BackendBindingSettings(
                binding_id="github-beta",
                provider="github",
                owner="owner",
                owner_type=ProjectOwnerType.USER,
                project_number=2,
            ),
        ),
        features=(("programme_status", FeatureMode.ENABLED),),
        gates=(("programme_drift", GateMode.ADVISORY),),
        evidence=EvidenceSettings(),
    )


def test_portfolio_status_preserves_project_identity_and_gaps() -> None:
    records = (
        WorkRecord(
            record_id="TASK-1",
            project_id="alpha-project",
            title="Blocked task",
            record_type=RecordType.TASK,
            state=LifecycleState.BLOCKED,
        ),
        WorkRecord(
            record_id="RISK-1",
            project_id="beta-project",
            title="Provider risk",
            record_type=RecordType.RISK,
            state=LifecycleState.ACTIVE,
        ),
        WorkRecord(
            record_id="SPEC-1",
            project_id="beta-project",
            title="Documentation due",
            record_type=RecordType.SPECIFICATION_SLICE,
            state=LifecycleState.DOCUMENTATION,
            documentation_milestone=(
                DocumentationMilestoneState.DOCUMENTATION_RECONCILIATION_DUE
            ),
            documentation_event_id="doc-event-1",
        ),
    )

    status = build_portfolio_status(
        settings(),
        records,
        traceability_gaps={"alpha-project": ("missing verification",)},
        provider_failures={"beta-project": "GitHub Project inaccessible"},
        truncated_projects=("beta-project",),
    )

    assert [item.project_id for item in status.projects] == [
        "alpha-project",
        "beta-project",
    ]
    alpha = status.project("alpha-project")
    beta = status.project("beta-project")
    assert alpha.blocker_ids == ("TASK-1",)
    assert alpha.traceability_gaps == ("missing verification",)
    assert beta.risk_ids == ("RISK-1",)
    assert beta.documentation_due_ids == ("SPEC-1",)
    assert beta.provider_failure == "GitHub Project inaccessible"
    assert beta.truncated is True
    assert status.total_records == 3


def test_status_rejects_records_for_unconfigured_projects() -> None:
    record = WorkRecord(
        record_id="TASK-9",
        project_id="unknown-project",
        title="Unknown",
        record_type=RecordType.TASK,
    )

    try:
        build_portfolio_status(settings(), (record,))
    except ValueError as exc:
        assert "unconfigured project" in str(exc)
    else:
        raise AssertionError("expected unconfigured project rejection")


def test_status_json_is_bounded_and_deterministic() -> None:
    status = build_portfolio_status(settings(), ())
    document = status.to_json_dict()

    assert document["portfolio_id"] == "default"
    assert document["total_records"] == 0
    assert [item["project_id"] for item in document["projects"]] == [
        "alpha-project",
        "beta-project",
    ]
