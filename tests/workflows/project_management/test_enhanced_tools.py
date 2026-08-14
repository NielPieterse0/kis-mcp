from __future__ import annotations

import asyncio
import json

import pytest
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from kis_mcp.work_management.backend import (
    ProjectBinding,
    ProjectFieldValue,
    ProjectInventory,
    ProjectItem,
    ProjectItemKind,
    ProjectOwnerType,
)
from kis_mcp.work_management.board import WorkBoardProjectionBridge
from kis_mcp.workflows.project_management.enhanced_tools import (
    register_project_management_enhancement_tools,
)


def _inventory() -> ProjectInventory:
    return ProjectInventory(
        binding=ProjectBinding(
            binding_id="github-default",
            managed_project_id="kis-mcp",
            provider_id="github-mcp",
            owner="NielPieterse0",
            owner_type=ProjectOwnerType.USER,
            project_number=1,
            repository="NielPieterse0/kis-mcp",
        ),
        title="KIS Work Management",
        items=(
            ProjectItem(
                item_id="item-215",
                kind=ProjectItemKind.ISSUE,
                title="Project Tasks Improvement Programme",
                repository="NielPieterse0/kis-mcp",
                number=215,
                state="OPEN",
                revision="rev-215",
                field_values=(
                    ProjectFieldValue("Status", "Active"),
                    ProjectFieldValue("Priority", "High"),
                    ProjectFieldValue("Effort", "Medium"),
                    ProjectFieldValue("Created", "2026-08-14T08:45:45Z"),
                    ProjectFieldValue("Blocked By", None),
                    ProjectFieldValue("Execution Owner", "agent-1"),
                    ProjectFieldValue("Record Type", "Task"),
                    ProjectFieldValue("Documentation Impact", "required"),
                    ProjectFieldValue("Change ID", "140-project-tasks-improvement-programme"),
                ),
            ),
        ),
    )


class _Service:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[str, ...], int]] = []

    async def read_inventory(
        self,
        project_id: str,
        *,
        field_names: tuple[str, ...] = (),
        item_limit: int = 100,
    ) -> ProjectInventory:
        self.calls.append((project_id, field_names, item_limit))
        return _inventory()


class _ProviderUnavailable(RuntimeError):
    error_code = "provider_unavailable"


class _FailingService:
    async def read_inventory(self, project_id: str, **kwargs):
        raise _ProviderUnavailable(f"provider unavailable for {project_id}")


def _tools(server: FastMCP):
    return list(asyncio.run(server.list_tools()))


def test_registers_three_bounded_read_only_tools() -> None:
    server = FastMCP("root")
    register_project_management_enhancement_tools(server, _Service())

    tools = _tools(server)
    assert {tool.name for tool in tools} == {
        "project_management_current_work",
        "project_management_board_data",
        "project_management_contract",
    }
    for tool in tools:
        assert tool.annotations is not None
        assert tool.annotations.readOnlyHint is True
        assert tool.annotations.destructiveHint is False
        assert tool.annotations.idempotentHint is True
        assert tool.annotations.openWorldHint is False


def test_current_work_returns_provenance_envelope_without_mutating_claim() -> None:
    server = FastMCP("root")
    service = _Service()
    register_project_management_enhancement_tools(server, service)

    result = asyncio.run(
        server.call_tool(
            "project_management_current_work",
            {"project_id": "kis-mcp", "execution_owner": "agent-1"},
        )
    ).structured_content

    assert result is not None
    assert result["resolved_target"] == {
        "project_id": "kis-mcp",
        "repository": "NielPieterse0/kis-mcp",
        "issue_number": 215,
    }
    assert result["provenance"]["authority"] == "configured_work_management_backend"
    assert result["result"]["status"] == "current"
    assert result["result"]["selected"]["change_id"] == "140-project-tasks-improvement-programme"
    assert service.calls[0][0] == "kis-mcp"


def test_board_data_publishes_exact_derived_snapshot_to_bridge() -> None:
    server = FastMCP("root")
    bridge = WorkBoardProjectionBridge()
    register_project_management_enhancement_tools(
        server,
        _Service(),
        board_bridge=bridge,
    )

    result = asyncio.run(
        server.call_tool(
            "project_management_board_data",
            {"project_id": "kis-mcp", "group_by": "owner"},
        )
    ).structured_content

    assert result is not None
    assert result["result"]["cards"][0]["number"] == 215
    assert result["result"]["groups"] == {"agent-1": ["item-215"]}
    bridge_value = bridge.current()
    assert bridge_value["status"] == "available"
    assert bridge_value["observed_at"] == result["result"]["observed_at"]
    assert bridge_value["cards"] == result["result"]["cards"]


def test_contract_describes_staged_result_and_mutation_semantics() -> None:
    server = FastMCP("root")
    register_project_management_enhancement_tools(server, _Service())

    result = asyncio.run(
        server.call_tool("project_management_contract", {})
    ).structured_content

    assert result is not None
    assert result["result_envelope"]["authority"] == "configured_work_management_backend"
    assert result["operations"]["project_management_board_data"] == "read"
    assert result["operations"]["project_management_claim_work"] == "preview_or_idempotent_mutation"
    assert "conflict" in result["typed_errors"]


def test_provider_failure_is_typed_json_in_tool_error() -> None:
    server = FastMCP("root")
    register_project_management_enhancement_tools(server, _FailingService())

    with pytest.raises(ToolError) as captured:
        asyncio.run(
            server.call_tool(
                "project_management_current_work",
                {"project_id": "kis-mcp", "execution_owner": "agent-1"},
            )
        )

    document = json.loads(str(captured.value))
    assert document["error_code"] == "provider_unavailable"
    assert document["retryable"] is True
    assert document["authority"] == "configured_work_management_backend"
