from __future__ import annotations

from kis_mcp.capabilities.contracts import OperationEffect
from kis_mcp.workflows.project_management import project_management_workflow_descriptors


def test_project_management_workflows_are_task_level_and_complete() -> None:
    descriptors = project_management_workflow_descriptors()
    by_id = {item.workflow_id: item for item in descriptors}

    assert set(by_id) == {
        "capture-project-work",
        "take-next-project-work",
        "manage-project-work-state",
        "persist-review-evidence",
        "inspect-project-schema",
        "sync-change-classification",
        "reconcile-project-state",
        "report-programme-status",
        "verify-change-traceability",
        "complete-work-managed-merge-queue",
        "complete-work-managed-pull-request",
    }
    assert by_id["capture-project-work"].required_steps == (
        "project_management_inventory",
        "project_management_reconcile",
    )
    assert by_id["take-next-project-work"].required_steps == (
        "project_management_take_next_work",
    )
    assert by_id["manage-project-work-state"].required_steps == (
        "project_management_transition_work",
        "project_management_hold_work",
        "project_management_defer_work",
        "project_management_release_work",
        "project_management_complete_work",
    )
    assert by_id["sync-change-classification"].required_steps == (
        "project_management_sync_change_classification",
    )
    assert by_id["inspect-project-schema"].required_steps == (
        "project_management_schema_status",
        "project_management_schema_plan",
    )
    assert by_id["persist-review-evidence"].effects == (OperationEffect.LOCAL_CHANGE,)
    assert by_id["reconcile-project-state"].effects == (
        OperationEffect.EXTERNAL,
        OperationEffect.LOCAL_CHANGE,
        OperationEffect.READ_ONLY,
    )
    assert by_id["complete-work-managed-pull-request"].required_steps == (
        "github_pull_request_read",
        "github_actions_list",
        "github_actions_get",
        "project_management_merge_readiness",
        "kis_github_merge_registered_pull_request",
        "project_management_documentation_reconcile",
    )
    assert all(
        "delete" not in " ".join(item.required_steps).casefold()
        and "graphql" not in " ".join(item.required_steps).casefold()
        for item in descriptors
    )
