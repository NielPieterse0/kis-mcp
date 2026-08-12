from kis_mcp.capabilities.contracts import OperationEffect
from kis_mcp.workflows.platform import workflow_descriptors


def test_execute_change_workflow_is_govern_recommendable_without_new_authority() -> None:
    workflows = {item.workflow_id: item for item in workflow_descriptors()}

    workflow = workflows["execute-current-change"]
    assert workflow.capabilities == ("operation.execute_change_workflow",)
    assert workflow.required_steps == ("execute_change_workflow",)
    assert workflow.executable_steps == ("execute_change_workflow",)
    assert workflow.effects == (OperationEffect.PROCESS,)
    assert "execute change workflow" in workflow.activation_terms
    assert "review" in workflow.description.casefold()
    assert "verification" in workflow.description.casefold()
