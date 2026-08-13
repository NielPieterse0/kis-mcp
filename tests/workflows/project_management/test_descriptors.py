from __future__ import annotations

from kis_mcp.capabilities.contracts import OperationEffect
from kis_mcp.workflows.project_management import project_management_workflow_descriptors


def test_project_management_workflows_are_task_level_and_complete() -> None:
    descriptors = project_management_workflow_descriptors()
    by_id = {item.workflow_id: item for item in descriptors}

    assert set(by_id) == {
        "capture-project-work",
        "persist-review-evidence",
        "inspect-project-schema",
        "reconcile-project-state",
        "report-programme-status",
        "verify-change-traceability",
        "complete-work-managed-pull-request",
    }
    assert by_id["capture-project-work"].required_steps == (
        "project_management_inventory",
        "project_management_reconcile",
    )
    assert by_id["persist-review-evidence"].effects == (
        OperationEffect.LOCAL_CHANGE,
    )
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
