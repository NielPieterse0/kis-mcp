from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from pathlib import Path

import pytest

from kis_mcp.work_management import (
    BackendBindingSettings,
    DocumentationImpact,
    DocumentationMode,
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
    RecordType,
    WorkManagementService,
    WorkManagementSettings,
    WorkRecord,
)
from kis_mcp.work_management.canonical_contracts import load_canonical_work_contracts


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
            "Todo",
            "Inbox",
            "Triage",
            "Proposed",
            "Approved",
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
    *,
    number: int = 177,
    revision: str = "rev-1",
    status: str = "Ready",
    owner: str | None = None,
    repository: str = "owner/alpha",
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
        item_id=f"item-{number}",
        kind=ProjectItemKind.ISSUE,
        title=f"Issue {number}",
        repository=repository,
        number=number,
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


class RecordingBackend(Backend):
    def __init__(self, item: ProjectItem) -> None:
        super().__init__(item)
        self.requested_fields: list[tuple[str, ...]] = []

    async def read_inventory(self, project_binding, *, field_names=(), item_limit=100):
        self.requested_fields.append(tuple(field_names))
        return await super().read_inventory(
            project_binding, field_names=field_names, item_limit=item_limit
        )


class BoundedInventoryBackend:
    def __init__(self, items: tuple[ProjectItem, ...]) -> None:
        self.items = list(items)
        self.applied = []
        self.read_limits: list[int] = []
        self.revision = 1

    async def read_inventory(self, project_binding, *, field_names=(), item_limit=100):
        del field_names
        self.read_limits.append(item_limit)
        truncated = len(self.items) > item_limit
        return ProjectInventory(
            binding=project_binding,
            title="Programme",
            fields=project_fields(),
            items=tuple(self.items[:item_limit]),
            truncated=truncated,
            next_cursor="next" if truncated else None,
        )

    async def apply_reconciliation(self, decision, *, idempotency_key: str):
        self.applied.append((decision, idempotency_key))
        index = next(
            index
            for index, item in enumerate(self.items)
            if item.item_id == decision.external_id
        )
        item = self.items[index]
        fields = {value.field_name: value.value for value in item.field_values}
        fields.update(dict(decision.desired_fields))
        self.revision += 1
        updated = replace(
            item,
            revision=f"rev-applied-{self.revision}",
            field_values=tuple(
                ProjectFieldValue(field_name=name, value=value)
                for name, value in fields.items()
            ),
        )
        self.items[index] = updated
        return ReconciliationOutcome(
            project_id=decision.project_id,
            record_id=decision.record_id,
            action=decision.action,
            applied=True,
            success=True,
            provider_revision=updated.revision,
            message="applied",
        )


def completion_record() -> WorkRecord:
    return WorkRecord(
        record_id="TASK-177",
        project_id="alpha-project",
        title="Complete exact target",
        record_type=RecordType.TASK,
        state=LifecycleState.DOCUMENTATION,
        documentation_mode=DocumentationMode.REQUIRED,
        documentation_impact=DocumentationImpact.NONE,
        documentation_rationale="No reader-facing behavior changed",
        documentation_reviewer="operator",
    )


def test_exact_target_claim_resolves_beyond_default_inventory_bound() -> None:
    backend = BoundedInventoryBackend(
        tuple(project_item(number=number) for number in range(1, 101))
        + (project_item(number=177),)
    )
    service = WorkManagementService(wm_settings(), {"github": backend})

    result = asyncio.run(
        service.claim_work(
            "alpha-project",
            "owner/alpha",
            177,
            "kis-dev/session-1",
            apply=False,
        )
    )

    assert result["mode"] == "preview"
    assert backend.read_limits[0] > 100


def test_claim_work_accepts_cross_repository_item_from_shared_project() -> None:
    backend = Backend(project_item(number=140, repository="owner/chatgpt-skill"))
    service = WorkManagementService(wm_settings(), {"github": backend})

    result = asyncio.run(
        service.claim_work(
            "alpha-project",
            "owner/chatgpt-skill",
            140,
            "kis-dev/session-1",
            apply=False,
        )
    )

    assert result["mode"] == "preview"
    decision, _key = backend.applied[0] if backend.applied else (None, None)
    assert decision is None


def test_complete_work_resolves_beyond_default_bound_and_preserves_revision() -> None:
    target = project_item(number=177, revision="rev-target-1", status="Active")
    backend = BoundedInventoryBackend(
        tuple(project_item(number=number) for number in range(1, 101)) + (target,)
    )
    service = WorkManagementService(wm_settings(), {"github": backend})

    result = asyncio.run(
        service.complete_work(
            "alpha-project",
            "owner/alpha",
            177,
            completion_record(),
            apply=True,
            idempotency_key="complete-177",
        )
    )

    decision, _key = backend.applied[0]
    assert decision.observed_revision == "rev-target-1"
    assert result["source_close_required"] is True
    inventory, reread, _settings = asyncio.run(
        service._issue_command_inventory("alpha-project", "owner/alpha", 177)
    )
    assert inventory.truncated is False
    assert reread.revision == result["outcomes"][0]["provider_revision"]
    values = {value.field_name: value.value for value in reread.field_values}
    assert values["Status"] == "Done"
    assert values["Delivery Stage"] == "Complete"


def test_exact_target_resolution_stays_fail_closed_when_bounded_scan_is_incomplete() -> None:
    backend = BoundedInventoryBackend(
        tuple(project_item(number=number) for number in range(1, 1002))
    )
    service = WorkManagementService(wm_settings(), {"github": backend})

    try:
        asyncio.run(
            service.claim_work(
                "alpha-project",
                "owner/alpha",
                1777,
                "kis-dev/session-1",
                apply=False,
            )
        )
    except ValueError as exc:
        assert "truncated Project inventory" in str(exc)
    else:
        raise AssertionError("incomplete exact-target inventory must fail closed")

    assert 100 < backend.read_limits[0] < len(backend.items)


def test_exact_target_resolution_rejects_observed_match_when_scan_stays_incomplete() -> None:
    target = project_item(number=177)
    hidden_duplicate = replace(target, item_id="item-177-hidden-duplicate")
    decoys = tuple(
        project_item(number=number)
        for number in range(1, 1001)
        if number != 177
    )
    backend = BoundedInventoryBackend((target, *decoys, hidden_duplicate))
    service = WorkManagementService(wm_settings(), {"github": backend})

    try:
        asyncio.run(
            service.claim_work(
                "alpha-project",
                "owner/alpha",
                177,
                "kis-dev/session-1",
                apply=False,
            )
        )
    except ValueError as exc:
        assert "truncated" in str(exc)
    else:
        raise AssertionError("incomplete exact-target resolution must not assume uniqueness")


def test_exact_target_resolution_reports_visible_duplicates_before_truncation() -> None:
    target = project_item(number=177)
    duplicate = replace(target, item_id="item-177-visible-duplicate")
    decoys = tuple(
        project_item(number=number)
        for number in range(1, 1000)
        if number != 177
    )
    backend = BoundedInventoryBackend(
        (target, duplicate, *decoys, project_item(number=1001))
    )
    service = WorkManagementService(wm_settings(), {"github": backend})

    try:
        asyncio.run(
            service.claim_work(
                "alpha-project",
                "owner/alpha",
                177,
                "kis-dev/session-1",
                apply=False,
            )
        )
    except ValueError as exc:
        assert "multiple Project items match" in str(exc)
    else:
        raise AssertionError("observed duplicate exact-target items must report ambiguity")


def test_exact_target_resolution_rejects_duplicate_matches_beyond_first_page() -> None:
    target = project_item(number=177)
    duplicate = replace(target, item_id="item-177-duplicate")
    backend = BoundedInventoryBackend(
        tuple(project_item(number=number) for number in range(1, 101))
        + (target, duplicate)
    )
    service = WorkManagementService(wm_settings(), {"github": backend})

    try:
        asyncio.run(
            service.claim_work(
                "alpha-project",
                "owner/alpha",
                177,
                "kis-dev/session-1",
                apply=False,
            )
        )
    except ValueError as exc:
        assert "multiple Project items match" in str(exc)
    else:
        raise AssertionError("duplicate exact-target Project items must fail closed")


def test_next_work_keeps_default_fail_closed_inventory_bound() -> None:
    backend = BoundedInventoryBackend(
        tuple(project_item(number=number) for number in range(1, 1002))
    )
    service = WorkManagementService(wm_settings(), {"github": backend})

    result = asyncio.run(service.next_work("alpha-project"))

    assert result.complete is False
    assert result.reasons == ("inventory_truncated",)
    assert backend.read_limits == [1000]


def test_next_work_reads_live_project_command_fields() -> None:
    backend = RecordingBackend(project_item())
    service = WorkManagementService(wm_settings(), {"github": backend})

    result = asyncio.run(service.next_work("alpha-project"))

    assert result.selected is not None
    assert result.selected.number == 177
    expected = set(load_canonical_work_contracts().selection.field_names)
    assert expected.issubset(set(backend.requested_fields[0]))


def test_exact_target_lifecycle_does_not_depend_on_selection_only_fields() -> None:
    probe_service = WorkManagementService(wm_settings(), {"github": RecordingBackend(project_item())})
    command_settings = probe_service._command_settings()
    command_fields = set(probe_service._command_field_names(command_settings))
    selection_only = set(load_canonical_work_contracts().selection.field_names) - command_fields

    claim_backend = RecordingBackend(project_item())
    claim_service = WorkManagementService(wm_settings(), {"github": claim_backend})
    claim = asyncio.run(
        claim_service.claim_work(
            "alpha-project", "owner/alpha", 177, "kis-dev/session-1", apply=False
        )
    )
    assert claim["mode"] == "preview"

    transition_backend = RecordingBackend(project_item())
    transition_service = WorkManagementService(
        wm_settings(), {"github": transition_backend}
    )
    transition = asyncio.run(
        transition_service.transition_work(
            "alpha-project", "owner/alpha", 177, LifecycleState.ACTIVE, apply=False
        )
    )
    assert transition["mode"] == "preview"

    completion_backend = RecordingBackend(project_item(status="Active"))
    completion_service = WorkManagementService(
        wm_settings(), {"github": completion_backend}
    )
    completion = asyncio.run(
        completion_service.complete_work(
            "alpha-project", "owner/alpha", 177, completion_record(), apply=False
        )
    )
    assert completion["mode"] == "preview"

    for backend in (claim_backend, transition_backend):
        requested = set(backend.requested_fields[0])
        assert requested.isdisjoint(selection_only)
        assert {"Status", "Priority", "Effort", "Execution Owner"}.issubset(requested)

    completion_requested = set(completion_backend.requested_fields[0])
    allowed_completion_extra = {command_settings.delivery.stage_field}
    assert completion_requested.isdisjoint(selection_only - allowed_completion_extra)
    assert allowed_completion_extra.issubset(completion_requested)


def test_provider_todo_intake_can_progress_through_command_plane_to_ready() -> None:
    backend = Backend(project_item(status="Todo"))
    service = WorkManagementService(wm_settings(), {"github": backend})

    asyncio.run(
        service.transition_work(
            "alpha-project", "owner/alpha", 177, LifecycleState.TRIAGE,
            apply=True, idempotency_key="todo-triage",
        )
    )
    asyncio.run(
        service.transition_work(
            "alpha-project", "owner/alpha", 177, LifecycleState.APPROVED,
            apply=True, idempotency_key="triage-approved",
        )
    )
    asyncio.run(
        service.transition_work(
            "alpha-project", "owner/alpha", 177, LifecycleState.READY,
            metadata={"__source_issue_body": "## Outcome\nValid\n\n## Acceptance criteria\nComplete"},
            apply=True, idempotency_key="approved-ready",
        )
    )

    values = {value.field_name: value.value for value in backend.item.field_values}
    assert values["Status"] == "Ready"


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


def _write_active_worktree_scope(
    root: Path,
    *,
    change_id: str,
    worktree_name: str,
    status: str = "active",
    declared_worktree: str | None = None,
) -> Path:
    worktree = root / ".work" / "worktrees" / worktree_name
    worktree.mkdir(parents=True)
    (worktree / ".git").write_text("gitdir: test", encoding="utf-8")
    scope_dir = worktree / ".work" / "changes" / change_id
    scope_dir.mkdir(parents=True)
    scope_path = scope_dir / "scope.json"
    scope_path.write_text(
        json.dumps(
            {
                "schema_version": 4,
                "change_id": change_id,
                "status": status,
                "worktree": declared_worktree
                or f".work/worktrees/{worktree_name}",
                "complexity": "medium",
                "risk_triggers": ["persistent_state"],
            }
        ),
        encoding="utf-8",
    )
    return scope_path


def test_change_classification_projects_active_worktree_scope(tmp_path: Path) -> None:
    change_id = "208-active-classification"
    _write_active_worktree_scope(
        tmp_path, change_id=change_id, worktree_name=change_id
    )
    backend = Backend(project_item(status="Active", owner="kis-dev/session-1"))
    service = WorkManagementService(wm_settings(str(tmp_path)), {"github": backend})

    result = asyncio.run(
        service.sync_change_classification(
            "alpha-project", "owner/alpha", 177, change_id, apply=False
        )
    )

    assert result["classification"] == {
        "change_id": change_id,
        "complexity": "medium",
        "risk_triggers": ["persistent_state"],
    }
    assert result["source_scope"] == (
        f".work/worktrees/{change_id}/.work/changes/{change_id}/scope.json"
    )


def test_change_classification_rejects_stale_active_worktree_scope(tmp_path: Path) -> None:
    change_id = "208-stale-classification"
    _write_active_worktree_scope(
        tmp_path, change_id=change_id, worktree_name=change_id, status="closed"
    )
    backend = Backend(project_item(status="Active", owner="kis-dev/session-1"))
    service = WorkManagementService(wm_settings(str(tmp_path)), {"github": backend})

    with pytest.raises(ValueError, match="scope is not active"):
        asyncio.run(
            service.sync_change_classification(
                "alpha-project", "owner/alpha", 177, change_id
            )
        )


def test_change_classification_rejects_mismatched_worktree_identity(tmp_path: Path) -> None:
    change_id = "208-mismatched-classification"
    _write_active_worktree_scope(
        tmp_path,
        change_id=change_id,
        worktree_name=change_id,
        declared_worktree=".work/worktrees/different-change",
    )
    backend = Backend(project_item(status="Active", owner="kis-dev/session-1"))
    service = WorkManagementService(wm_settings(str(tmp_path)), {"github": backend})

    with pytest.raises(ValueError, match="worktree identity mismatch"):
        asyncio.run(
            service.sync_change_classification(
                "alpha-project", "owner/alpha", 177, change_id
            )
        )


def test_change_classification_rejects_ambiguous_active_worktrees(tmp_path: Path) -> None:
    change_id = "208-ambiguous-classification"
    _write_active_worktree_scope(
        tmp_path, change_id=change_id, worktree_name="first-active"
    )
    _write_active_worktree_scope(
        tmp_path, change_id=change_id, worktree_name="second-active"
    )
    backend = Backend(project_item(status="Active", owner="kis-dev/session-1"))
    service = WorkManagementService(wm_settings(str(tmp_path)), {"github": backend})

    with pytest.raises(ValueError, match="scope is ambiguous"):
        asyncio.run(
            service.sync_change_classification(
                "alpha-project", "owner/alpha", 177, change_id
            )
        )


def test_primary_change_scope_wins_over_active_worktree_fallback(tmp_path: Path) -> None:
    change_id = "208-landed-classification"
    primary = tmp_path / ".work" / "changes" / change_id
    primary.mkdir(parents=True)
    (primary / "scope.json").write_text(
        json.dumps(
            {
                "schema_version": 4,
                "change_id": change_id,
                "complexity": "small",
                "risk_triggers": [],
            }
        ),
        encoding="utf-8",
    )
    _write_active_worktree_scope(
        tmp_path, change_id=change_id, worktree_name="stale-leftover"
    )
    backend = Backend(project_item(status="Active", owner="kis-dev/session-1"))
    service = WorkManagementService(wm_settings(str(tmp_path)), {"github": backend})

    result = asyncio.run(
        service.sync_change_classification(
            "alpha-project", "owner/alpha", 177, change_id, apply=False
        )
    )

    assert result["classification"]["complexity"] == "small"
    assert result["source_scope"] == f".work/changes/{change_id}/scope.json"


def test_progress_triage_applies_declared_edges_and_fingerprint_noop() -> None:
    backend = Backend(project_item(status="Triage"))
    service = WorkManagementService(wm_settings(), {"github": backend})
    body = "## Outcome\nDefined\n\n## Acceptance criteria\nVerified"

    preview = asyncio.run(
        service.progress_triage("alpha-project", "owner/alpha", 177, body)
    )
    assert preview["attention"] is False
    assert preview["planned_transitions"] == ["approved", "ready"]

    unchanged = asyncio.run(
        service.progress_triage(
            "alpha-project", "owner/alpha", 177, body,
            previous_fingerprint=preview["evaluation"]["fingerprint"],
        )
    )
    assert unchanged["mode"] == "unchanged"

    applied = asyncio.run(
        service.progress_triage(
            "alpha-project", "owner/alpha", 177, body,
            previous_fingerprint=preview["evaluation"]["fingerprint"],
            apply=True, idempotency_key="triage-177",
        )
    )
    assert len(applied["transitions"]) == 2
    values = {value.field_name: value.value for value in backend.item.field_values}
    assert values["Status"] == "Ready"


class FailReadyOnceBackend(Backend):
    def __init__(self, item: ProjectItem) -> None:
        super().__init__(item)
        self.failed_ready = False

    async def apply_reconciliation(self, decision, *, idempotency_key: str):
        desired = dict(decision.desired_fields)
        if desired.get("Status") == "Ready" and not self.failed_ready:
            self.failed_ready = True
            raise RuntimeError("injected ready transition failure")
        return await super().apply_reconciliation(
            decision, idempotency_key=idempotency_key
        )


def test_progress_triage_resumes_from_approved_after_partial_failure() -> None:
    backend = FailReadyOnceBackend(project_item(status="Triage"))
    service = WorkManagementService(wm_settings(), {"github": backend})
    body = "## Outcome\nDefined\n\n## Acceptance criteria\nVerified"
    preview = asyncio.run(
        service.progress_triage("alpha-project", "owner/alpha", 177, body)
    )
    fingerprint = preview["evaluation"]["fingerprint"]
    with pytest.raises(RuntimeError, match="injected ready transition failure"):
        asyncio.run(service.progress_triage(
            "alpha-project", "owner/alpha", 177, body,
            previous_fingerprint=fingerprint,
            apply=True, idempotency_key="triage-resume-177",
        ))
    assert dict((v.field_name, v.value) for v in backend.item.field_values)["Status"] == "Approved"
    resumed = asyncio.run(service.progress_triage(
        "alpha-project", "owner/alpha", 177, body,
        previous_fingerprint=fingerprint,
        apply=True, idempotency_key="triage-resume-177",
    ))
    assert resumed["current_state"] == "approved"
    assert resumed["planned_transitions"] == ["ready"]
    assert len(resumed["transitions"]) == 1
    values = {value.field_name: value.value for value in backend.item.field_values}
    assert values["Status"] == "Ready"


def test_progress_triage_apply_requires_matching_preview_fingerprint() -> None:
    backend = Backend(project_item(status="Triage"))
    service = WorkManagementService(wm_settings(), {"github": backend})
    body = "## Outcome\nDefined\n\n## Acceptance criteria\nVerified"

    with pytest.raises(ValueError, match="previous_fingerprint"):
        asyncio.run(service.progress_triage(
            "alpha-project", "owner/alpha", 177, body,
            apply=True, idempotency_key="triage-177",
        ))
    with pytest.raises(ValueError, match="fingerprint changed"):
        asyncio.run(service.progress_triage(
            "alpha-project", "owner/alpha", 177, body,
            previous_fingerprint="stale", apply=True,
            idempotency_key="triage-177",
        ))

    values = {value.field_name: value.value for value in backend.item.field_values}
    assert values["Status"] == "Triage"


def test_progress_triage_fingerprint_is_bound_to_exact_issue_identity() -> None:
    body = "## Outcome\nDefined\n\n## Acceptance criteria\nVerified"
    first_service = WorkManagementService(
        wm_settings(), {"github": Backend(project_item(number=177, status="Triage"))}
    )
    preview = asyncio.run(
        first_service.progress_triage("alpha-project", "owner/alpha", 177, body)
    )

    second_backend = Backend(project_item(number=178, status="Triage"))
    second_service = WorkManagementService(wm_settings(), {"github": second_backend})
    with pytest.raises(ValueError, match="fingerprint changed"):
        asyncio.run(second_service.progress_triage(
            "alpha-project", "owner/alpha", 178, body,
            previous_fingerprint=preview["evaluation"]["fingerprint"],
            apply=True, idempotency_key="triage-178",
        ))
    values = {value.field_name: value.value for value in second_backend.item.field_values}
    assert values["Status"] == "Triage"


def test_non_ready_triage_apply_still_requires_exact_preview_fingerprint() -> None:
    backend = Backend(project_item(status="Triage"))
    service = WorkManagementService(wm_settings(), {"github": backend})
    body = "## Outcome\nDefined"
    preview = asyncio.run(
        service.progress_triage("alpha-project", "owner/alpha", 177, body)
    )
    fingerprint = preview["evaluation"]["fingerprint"]

    with pytest.raises(ValueError, match="previous_fingerprint"):
        asyncio.run(service.progress_triage(
            "alpha-project", "owner/alpha", 177, body, apply=True,
        ))
    with pytest.raises(ValueError, match="fingerprint changed"):
        asyncio.run(service.progress_triage(
            "alpha-project", "owner/alpha", 177, body,
            previous_fingerprint="stale", apply=True,
        ))
    attention = asyncio.run(service.progress_triage(
        "alpha-project", "owner/alpha", 177, body,
        previous_fingerprint=fingerprint, apply=True,
    ))
    assert attention["attention"] is True
    assert "transitions" not in attention
