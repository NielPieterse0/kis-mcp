from __future__ import annotations

from kis_mcp.capabilities.contracts import OperationEffect
from kis_mcp.capabilities.settings import load_capability_settings
from kis_mcp.capabilities.surface import capability_control_contribution
from kis_mcp.workflows.platform import workflow_descriptors

REFRESH = "kis_github_refresh_registered_default_branch"


def test_refresh_descriptor_is_bounded_and_not_direct() -> None:
    operations = {
        item.name: item for item in capability_control_contribution().operations
    }
    refresh = operations[REFRESH]

    assert set(refresh.effects) == {
        OperationEffect.EXTERNAL,
        OperationEffect.LOCAL_CHANGE,
    }
    assert refresh.approval_required is True
    assert "registered-github" in refresh.tags
    assert "virtual" in refresh.tags
    assert "approved" in refresh.input_schema["required"]
    assert "expected_remote_default" in refresh.input_schema["required"]
    settings = load_capability_settings()
    assert REFRESH not in settings.direct_operations


def test_safe_closeout_refreshes_tracking_immediately_after_merge() -> None:
    closeout = next(
        item
        for item in workflow_descriptors()
        if item.workflow_id == "pull-request-safe-closeout"
    )
    merge_index = closeout.required_steps.index(
        "kis_github_merge_registered_pull_request"
    )
    assert closeout.required_steps[merge_index + 1] == REFRESH
    assert "kis_github_delete_registered_branch" not in closeout.required_steps
    assert "operation.kis_github_delete_registered_branch" not in closeout.capabilities
    assert "remote review branch is retained" in closeout.completion_criteria
    assert (
        "operation.kis_github_refresh_registered_default_branch"
        in closeout.capabilities
    )


def test_registered_change_refreshes_tracking_before_worktree_creation() -> None:
    develop = next(
        item
        for item in workflow_descriptors()
        if item.workflow_id == "develop-isolated-change"
    )
    create_index = develop.required_steps.index("create_change_worktree")
    assert develop.required_steps[create_index - 1] == REFRESH
    assert (
        "operation.kis_github_refresh_registered_default_branch" in develop.capabilities
    )
    assert OperationEffect.EXTERNAL in develop.effects


def test_work_managed_merge_inherits_post_merge_tracking_refresh() -> None:
    managed = next(
        item
        for item in workflow_descriptors()
        if item.workflow_id == "complete-work-managed-pull-request"
    )
    merge_index = managed.required_steps.index(
        "kis_github_merge_registered_pull_request"
    )
    assert managed.required_steps[merge_index + 1] == REFRESH
    assert (
        "operation.kis_github_refresh_registered_default_branch" in managed.capabilities
    )
