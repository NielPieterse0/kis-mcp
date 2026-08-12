from kis_mcp.workflows.platform import workflow_descriptors


def test_agnix_workflow_uses_runtime_operation_capability() -> None:
    workflows = {item.workflow_id: item for item in workflow_descriptors()}
    workflow = workflows["validate-agent-configuration"]

    assert workflow.capabilities == ("operation.validate_agent_configuration",)
    assert workflow.required_steps == ("validate_agent_configuration",)
    assert workflow.executable_steps == ("validate_agent_configuration",)
    assert workflow.effects == ("process",)
