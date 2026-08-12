from kis_mcp.capabilities.contracts import OperationEffect
from kis_mcp.workflows.platform import workflow_descriptors


def test_reviewable_pr_completion_workflow_stops_before_closeout() -> None:
    workflows = {item.workflow_id: item for item in workflow_descriptors()}
    workflow = workflows["prepare-reviewable-pull-request"]

    assert workflow.required_steps == ("prepare_reviewable_pull_request",)
    assert workflow.executable_steps == ("prepare_reviewable_pull_request",)
    assert "operation.execute_change_workflow" in workflow.capabilities
    assert "operation.kis_github_reconcile_registered_commit" in workflow.capabilities
    assert "operation.kis_github_create_registered_pull_request" in workflow.capabilities
    assert workflow.effects == (OperationEffect.EXTERNAL, OperationEffect.PROCESS)
    assert "merge" not in workflow.description.casefold()
    assert "delete" not in workflow.description.casefold()
    assert "cleanup" not in workflow.description.casefold()
