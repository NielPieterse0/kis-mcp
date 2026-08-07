from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from kis_mcp.work_management import (
    BackendBindingSettings,
    DesiredProjection,
    EvidenceSettings,
    FeatureMode,
    GateMode,
    ManagedProject,
    ObservedProjection,
    ProjectInventory,
    ProjectOwnerType,
    ReconciliationOutcome,
    ReviewArtifactKind,
    ReviewEvidenceStore,
    WorkManagementService,
    WorkManagementSettings,
    WorkManagementUnavailable,
    create_review_evidence_manifest,
)


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
        ),
        backend_bindings=(
            BackendBindingSettings(
                binding_id="github-alpha",
                provider="github",
                owner="owner",
                owner_type=ProjectOwnerType.USER,
                project_number=7,
            ),
        ),
        features=(("reconciliation", FeatureMode.ENABLED),),
        automation=(),
        gates=(("programme_drift", GateMode.ADVISORY),),
        evidence=EvidenceSettings(),
    )


class Backend:
    def __init__(self) -> None:
        self.bindings = []
        self.applied = []

    async def read_inventory(
        self,
        project_binding,
        *,
        field_names=(),
        item_limit=100,
    ) -> ProjectInventory:
        del field_names, item_limit
        self.bindings.append(project_binding)
        return ProjectInventory(binding=project_binding, title="Programme")

    async def apply_reconciliation(
        self,
        decision,
        *,
        idempotency_key: str,
    ) -> ReconciliationOutcome:
        self.applied.append((decision, idempotency_key))
        return ReconciliationOutcome(
            project_id=decision.project_id,
            record_id=decision.record_id,
            action=decision.action,
            applied=True,
            success=True,
            provider_revision="rev-2",
        )


def test_service_resolves_project_binding_without_process_state() -> None:
    backend = Backend()
    service = WorkManagementService(settings(), {"github": backend})

    inventory = asyncio.run(service.read_inventory("alpha-project"))

    assert inventory.binding.managed_project_id == "alpha-project"
    assert inventory.binding.project_number == 7
    assert backend.bindings[0].repository == "owner/alpha"


def test_missing_provider_is_corrective_and_not_an_hr_violation() -> None:
    service = WorkManagementService(settings(), {})

    with pytest.raises(WorkManagementUnavailable) as raised:
        asyncio.run(service.read_inventory("alpha-project"))

    assert raised.value.error_code == "provider_unavailable"
    assert "HR-" not in str(raised.value)


def test_service_coordinates_dry_run_and_apply() -> None:
    backend = Backend()
    service = WorkManagementService(settings(), {"github": backend})
    desired = (
        DesiredProjection(
            project_id="alpha-project",
            record_id="TASK-1",
            fields=(("Status", "Active"),),
        ),
    )
    observed = (
        ObservedProjection(
            project_id="alpha-project",
            record_id="TASK-1",
            fields=(("Status", "Inbox"),),
            revision="rev-1",
        ),
    )

    preview = asyncio.run(
        service.reconcile(
            "alpha-project",
            desired,
            observed,
            supported_fields=("Status",),
        )
    )
    applied = asyncio.run(
        service.reconcile(
            "alpha-project",
            desired,
            observed,
            supported_fields=("Status",),
            apply=True,
            idempotency_key="reconcile-alpha-1",
        )
    )

    assert preview[0].applied is False
    assert applied[0].applied is True
    assert backend.applied[0][1] == "reconcile-alpha-1:TASK-1"


def test_service_persists_review_evidence_through_project_store(tmp_path: Path) -> None:
    backend = Backend()
    service = WorkManagementService(
        settings(),
        {"github": backend},
        evidence_store_factory=lambda _project, limits: ReviewEvidenceStore(
            tmp_path,
            max_file_bytes=limits.max_file_bytes,
            max_total_bytes=limits.max_total_bytes,
        ),
    )
    manifest = create_review_evidence_manifest("REV-200")

    result = service.persist_review_artifact(
        "alpha-project",
        manifest,
        ReviewArtifactKind.REPORT,
        "# Durable report\n",
    )

    assert result.path == ".work/reviews/REV-200/report.md"
    assert (tmp_path / result.path).read_text(encoding="utf-8") == "# Durable report\n"
