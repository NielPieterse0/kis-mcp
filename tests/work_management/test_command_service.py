from __future__ import annotations

import asyncio
from dataclasses import replace
import json
from pathlib import Path

from kis_mcp.work_management import (
    BackendBindingSettings,
    EvidenceSettings,
    FeatureMode,
    LifecycleState,
    ManagedProject,
    ProjectField,
    ProjectFieldKind,
    ProjectFieldOption,
    ProjectFieldValue,
    ProjectInventory,
    ProjectItem,
    ProjectItemKind,
    ProjectOwnerType,
    ReconciliationOutcome,
    WorkManagementService,
    WorkManagementSettings,
)


def option(name: str) -> ProjectFieldOption:
    return ProjectFieldOption(
        option_id=f"o-{name.lower().replace(' ', '-')}", name=name
    )


def field(name: str, kind: ProjectFieldKind, *options: str) -> ProjectField:
    return ProjectField(
        field_id=f"f-{name.lower().replace(' ', '-')}",
        name=name,
        kind=kind,
        options=tuple(option(value) for value in options),
    )


def project_fields() -> tuple[ProjectField, ...]:
    return (
        field(
            "Status",
            ProjectFieldKind.SINGLE_SELECT,
            "Ready",
            "Active",
            "On Hold",
            "Deferred",
            "Done",
        ),
        field(
            "Priority",
            ProjectFieldKind.SINGLE_SELECT,
            "Critical",
            "High",
            "Medium",
            "Low",
        ),
        field(
            "Effort", ProjectFieldKind.SINGLE_SELECT, "Tiny", "Small", "Medium", "Large"
        ),
        field(
            "Record Type", ProjectFieldKind.SINGLE_SELECT, "Task", "Specification Slice"
        ),
        field(
            "Documentation Impact",
            ProjectFieldKind.SINGLE_SELECT,
            "Not Assessed",
            "None",
            "Planned",
            "In Progress",
            "Pre-merge Complete",
            "Post-merge Complete",
        ),
        field("Execution Owner", ProjectFieldKind.TEXT),
        field("Review Trigger", ProjectFieldKind.TEXT),
        field("Blocked By", ProjectFieldKind.TEXT),
        field("Created", ProjectFieldKind.DATE),
        field(
            "Delivery Stage",
            ProjectFieldKind.SINGLE_SELECT,
            "None",
            "Change Created",
            "Implementing",
            "Complete",
        ),
        field("Change ID", ProjectFieldKind.TEXT),
        field("Complexity", ProjectFieldKind.SINGLE_SELECT, "Small", "Medium", "Large"),
        field("Risk Triggers", ProjectFieldKind.TEXT),
    )


def project_item(
    *, revision: str = "rev-1", status: str = "Ready", owner: str | None = None
) -> ProjectItem:
    values = [
        ProjectFieldValue(field_name="Status", value=status),
        ProjectFieldValue(field_name="Priority", value="High"),
        ProjectFieldValue(field_name="Effort", value="Small"),
        ProjectFieldValue(field_name="Record Type", value="Task"),
        ProjectFieldValue(field_name="Documentation Impact", value="Planned"),
        ProjectFieldValue(field_name="Blocked By", value=None),
    ]
    if owner is not None:
        values.append(ProjectFieldValue(field_name="Execution Owner", value=owner))
    return ProjectItem(
        item_id="item-177",
        kind=ProjectItemKind.ISSUE,
        title="Restore Work Management command plane",
        repository="owner/alpha",
        number=177,
        state="OPEN",
        revision=revision,
        field_values=tuple(values),
    )


def wm_settings(local_root: str = "C:\\Projects\\alpha") -> WorkManagementSettings:
    return WorkManagementSettings(
        enabled=True,
        portfolio_id="default",
        managed_projects=(
            ManagedProject(
                project_id="alpha-project",
                local_root=local_root,
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
                project_number=1,
            ),
        ),
        features=(("reconciliation", FeatureMode.ENABLED),),
        automation=(),
        gates=(),
        evidence=EvidenceSettings(),
    )


class Backend:
    def __init__(self, item: ProjectItem) -> None:
        self.item = item
        self.applied = []
        self.revision = 1

    async def read_inventory(self, project_binding, *, field_names=(), item_limit=100):
        del field_names, item_limit
        return ProjectInventory(
            binding=project_binding,
            title="Programme",
            fields=project_fields(),
            items=(self.item,),
        )

    async def apply_reconciliation(self, decision, *, idempotency_key: str):
        self.applied.append((decision, idempotency_key))
        fields = {value.field_name: value.value for value in self.item.field_values}
        fields.update(dict(decision.desired_fields))
        self.revision += 1
        self.item = replace(
            self.item,
            revision=f"rev-{self.revision}",
            field_values=tuple(
                ProjectFieldValue(field_name=name, value=value)
                for name, value in fields.items()
            ),
        )
        return ReconciliationOutcome(
            project_id=decision.project_id,
            record_id=decision.record_id,
            action=decision.action,
            applied=True,
            success=True,
            provider_revision=self.item.revision,
            message="applied",
        )


def test_next_work_reads_live_project_command_fields() -> None:
    backend = Backend(project_item())
    service = WorkManagementService(wm_settings(), {"github": backend})

    result = asyncio.run(service.next_work("alpha-project"))

    assert result.selected is not None
    assert result.selected.number == 177


def test_claim_is_two_phase_and_verifies_owner_before_activation() -> None:
    backend = Backend(project_item())
    service = WorkManagementService(wm_settings(), {"github": backend})

    result = asyncio.run(
        service.claim_work(
            "alpha-project",
            "owner/alpha",
            177,
            "kis-dev/session-1",
            apply=True,
            idempotency_key="claim-177",
        )
    )

    assert result["phase"] == "active"
    assert [key for _decision, key in backend.applied] == [
        "claim-177:claim:WORK-177",
        "claim-177:activate:WORK-177",
    ]
    values = {value.field_name: value.value for value in backend.item.field_values}
    assert values["Execution Owner"] == "kis-dev/session-1"
    assert values["Status"] == "Active"


def test_hold_requires_review_trigger_from_settings() -> None:
    backend = Backend(project_item(status="Active", owner="kis-dev/session-1"))
    service = WorkManagementService(wm_settings(), {"github": backend})

    try:
        asyncio.run(
            service.transition_work(
                "alpha-project",
                "owner/alpha",
                177,
                LifecycleState.ON_HOLD,
                apply=False,
            )
        )
    except ValueError as exc:
        assert "Review Trigger" in str(exc)
    else:
        raise AssertionError("On Hold without Review Trigger must fail")

    preview = asyncio.run(
        service.transition_work(
            "alpha-project",
            "owner/alpha",
            177,
            LifecycleState.ON_HOLD,
            metadata={"Review Trigger": "Operator review"},
            apply=False,
        )
    )
    assert preview["mode"] == "preview"


def test_transition_metadata_cannot_override_evidence_owned_fields() -> None:
    backend = Backend(project_item(status="Active", owner="kis-dev/session-1"))
    service = WorkManagementService(wm_settings(), {"github": backend})

    try:
        asyncio.run(
            service.transition_work(
                "alpha-project",
                "owner/alpha",
                177,
                LifecycleState.ON_HOLD,
                metadata={
                    "Review Trigger": "Operator review",
                    "Complexity": "Small",
                },
                apply=False,
            )
        )
    except ValueError as exc:
        assert "evidence-owned" in str(exc)
    else:
        raise AssertionError(
            "transition metadata must not overwrite evidence-owned fields"
        )


def test_transition_metadata_cannot_modify_execution_claim() -> None:
    backend = Backend(project_item(status="Active", owner="kis-dev/session-1"))
    service = WorkManagementService(wm_settings(), {"github": backend})

    try:
        asyncio.run(
            service.transition_work(
                "alpha-project",
                "owner/alpha",
                177,
                LifecycleState.ON_HOLD,
                metadata={
                    "Review Trigger": "Operator review",
                    "Execution Owner": "kis-dev/session-2",
                },
                apply=False,
            )
        )
    except ValueError as exc:
        assert "claim" in str(exc)
    else:
        raise AssertionError("transition metadata must not modify execution claims")


def test_claimed_work_cannot_transition_to_ready_without_release() -> None:
    backend = Backend(project_item(status="Active", owner="kis-dev/session-1"))
    service = WorkManagementService(wm_settings(), {"github": backend})

    try:
        asyncio.run(
            service.transition_work(
                "alpha-project",
                "owner/alpha",
                177,
                LifecycleState.READY,
                apply=False,
            )
        )
    except ValueError as exc:
        assert "release_work" in str(exc)
    else:
        raise AssertionError("claimed work must use release_work before Ready")


def test_release_requires_exact_owner_and_returns_ready() -> None:
    backend = Backend(project_item(status="Active", owner="kis-dev/session-1"))
    service = WorkManagementService(wm_settings(), {"github": backend})

    asyncio.run(
        service.release_work(
            "alpha-project",
            "owner/alpha",
            177,
            "kis-dev/session-1",
            apply=True,
            idempotency_key="release-177",
        )
    )
    values = {value.field_name: value.value for value in backend.item.field_values}
    assert values["Status"] == "Ready"
    assert values["Execution Owner"] is None


def test_take_next_work_composes_selection_and_claim() -> None:
    backend = Backend(project_item())
    service = WorkManagementService(wm_settings(), {"github": backend})

    result = asyncio.run(
        service.take_next_work(
            "alpha-project",
            "kis-dev/session-2",
            apply=False,
            idempotency_key="take-177",
        )
    )

    assert result["selection"]["selected"]["number"] == 177
    assert result["claim"]["mode"] == "preview"


def test_change_classification_projects_authoritative_scope(tmp_path: Path) -> None:
    change_id = "125-work-management-command-plane"
    scope_dir = tmp_path / ".work" / "changes" / change_id
    scope_dir.mkdir(parents=True)
    (scope_dir / "scope.json").write_text(
        json.dumps(
            {
                "schema_version": 4,
                "change_id": change_id,
                "complexity": "large",
                "risk_triggers": ["public_contract", "architecture_boundary"],
            }
        ),
        encoding="utf-8",
    )
    backend = Backend(project_item(status="Active", owner="kis-dev/session-1"))
    service = WorkManagementService(wm_settings(str(tmp_path)), {"github": backend})

    result = asyncio.run(
        service.sync_change_classification(
            "alpha-project",
            "owner/alpha",
            177,
            change_id,
            apply=True,
            idempotency_key="classification-177",
        )
    )

    values = {value.field_name: value.value for value in backend.item.field_values}
    assert result["classification"]["complexity"] == "large"
    assert result["classification"]["risk_triggers"] == [
        "architecture_boundary",
        "public_contract",
    ]
    assert values["Change ID"] == change_id
    assert values["Complexity"] == "Large"
    assert values["Risk Triggers"] == "architecture_boundary, public_contract"
    assert values["Delivery Stage"] == "Change Created"
