from __future__ import annotations

import asyncio

from fastmcp import FastMCP

from kis_mcp.work_management.backend import ProjectBinding, ProjectFieldValue, ProjectInventory, ProjectItem, ProjectItemKind, ProjectOwnerType
from kis_mcp.workflows.project_management.enhanced_tools import register_project_management_enhancement_tools


def _inventory(owner: str = "agent-b") -> ProjectInventory:
    return ProjectInventory(
        binding=ProjectBinding(binding_id="github-default", managed_project_id="kis-mcp", provider_id="github-mcp", owner="NielPieterse0", owner_type=ProjectOwnerType.USER, project_number=1, repository="NielPieterse0/kis-mcp"),
        title="KIS Work Management",
        items=(ProjectItem(item_id="item-544", kind=ProjectItemKind.ISSUE, title="Pull assignment", repository="NielPieterse0/kis-mcp", number=544, state="OPEN", revision="rev-544", field_values=(ProjectFieldValue("Status", "Active"), ProjectFieldValue("Priority", "Critical"), ProjectFieldValue("Effort", "Large"), ProjectFieldValue("Created", "2026-08-27T14:34:47Z"), ProjectFieldValue("Blocked By", None), ProjectFieldValue("Execution Owner", owner), ProjectFieldValue("Record Type", "Specification Slice"), ProjectFieldValue("Documentation Impact", "Planned"), ProjectFieldValue("Change ID", "641-pull-based-assignment-handoff"))),),
    )


class _Service:
    def __init__(self, owner: str = "agent-b") -> None:
        self.owner = owner

    async def read_inventory(self, project_id: str, **kwargs) -> ProjectInventory:
        return _inventory(self.owner)


def test_current_work_materializes_deterministic_handoff_after_owner_reread() -> None:
    calls: list[tuple[str, str, int]] = []

    async def materialize(project_id: str, repository: str, issue_number: int):
        calls.append((project_id, repository, issue_number))
        return {"schema_version": 2, "work_id": f"WORK-{issue_number}", "execution_owner": "agent-b", "generation": 3, "run_id": "run-3", "lease_id": "lease-3", "fence_token": 9}

    server = FastMCP("root")
    register_project_management_enhancement_tools(server, _Service(), activation_materializer=materialize)
    result = asyncio.run(server.call_tool("project_management_current_work", {"project_id": "kis-mcp", "execution_owner": "agent-b"})).structured_content

    assert result is not None
    assert calls == [("kis-mcp", "NielPieterse0/kis-mcp", 544)]
    assert result["result"]["task_handoff"]["work_id"] == "WORK-544"
    assert result["result"]["task_handoff"]["lease_id"] == "lease-3"
    assert result["result"]["task_handoff"]["fence_token"] == 9


def test_current_work_does_not_materialize_for_different_execution_owner() -> None:
    calls: list[tuple[str, str, int]] = []

    async def materialize(project_id: str, repository: str, issue_number: int):
        calls.append((project_id, repository, issue_number))
        return {"work_id": f"WORK-{issue_number}"}

    server = FastMCP("root")
    register_project_management_enhancement_tools(server, _Service(owner="agent-a"), activation_materializer=materialize)
    result = asyncio.run(server.call_tool("project_management_current_work", {"project_id": "kis-mcp", "execution_owner": "agent-b"})).structured_content

    assert result is not None
    assert result["result"]["selected"] is None
    assert "task_handoff" not in result["result"]
    assert calls == []


def test_project_management_registration_forwards_assignment_materializer_to_resume() -> None:
    from kis_mcp.workflows.project_management import register_project_management_tools

    calls: list[tuple[str, str, int]] = []

    async def materialize(project_id: str, repository: str, issue_number: int):
        calls.append((project_id, repository, issue_number))
        return {"work_id": f"WORK-{issue_number}", "execution_owner": "agent-b"}

    server = FastMCP("root")
    register_project_management_tools(
        server, _Service(), activation_materializer=materialize
    )
    result = asyncio.run(
        server.call_tool(
            "project_management_current_work",
            {"project_id": "kis-mcp", "execution_owner": "agent-b"},
        )
    ).structured_content

    assert result is not None
    assert result["result"]["task_handoff"]["execution_owner"] == "agent-b"
    assert calls == [("kis-mcp", "NielPieterse0/kis-mcp", 544)]
