from __future__ import annotations

import asyncio
import json

import pytest
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from kis_mcp.providers.github.projects import GitHubProjectInventoryAdapter
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
        self.calls: list[tuple[str, tuple[str, ...], int, str | None]] = []

    async def read_inventory(
        self,
        project_id: str,
        *,
        field_names: tuple[str, ...] = (),
        item_limit: int = 100,
        query: str | None = None,
    ) -> ProjectInventory:
        self.calls.append((project_id, field_names, item_limit, query))
        return _inventory()


class _ProviderUnavailable(RuntimeError):
    error_code = "provider_unavailable"


class _FailingService:
    async def read_inventory(self, project_id: str, **kwargs):
        raise _ProviderUnavailable(f"provider unavailable for {project_id}")


def _tools(server: FastMCP):
    return list(asyncio.run(server.list_tools()))


def test_registers_three_bounded_read_only_tools_with_effect_scope() -> None:
    server = FastMCP("root")
    register_project_management_enhancement_tools(server, _Service())

    tools = {tool.name: tool for tool in _tools(server)}
    assert set(tools) == {
        "project_management_current_work",
        "project_management_board_data",
        "project_management_contract",
    }
    for tool in tools.values():
        assert tool.annotations is not None
        assert tool.annotations.read_only_hint is True
        assert tool.annotations.destructive_hint is False
        assert tool.annotations.idempotent_hint is True
    assert tools["project_management_current_work"].annotations.open_world_hint is True
    assert tools["project_management_board_data"].annotations.open_world_hint is True
    assert tools["project_management_contract"].annotations.open_world_hint is False


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
    assert service.calls[0][2] == 1000


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


def test_contract_describes_every_project_management_operation() -> None:
    server = FastMCP("root")
    register_project_management_enhancement_tools(server, _Service())

    result = asyncio.run(
        server.call_tool("project_management_contract", {})
    ).structured_content

    assert result is not None
    assert result["result_envelope"]["authority"] == "configured_work_management_backend"
    operations = result["operations"]
    assert operations["project_management_board_data"] == "external_read"
    assert operations["project_management_claim_work"] == (
        "preview_or_idempotent_external_mutation"
    )
    assert operations["project_management_persist_review"] == "local_idempotent_persistence"
    assert set(operations) == {
        "project_management_inventory",
        "project_management_reconcile",
        "project_management_next_work",
        "project_management_take_next_work",
        "project_management_claim_work",
        "project_management_release_work",
        "project_management_transition_work",
        "project_management_hold_work",
        "project_management_defer_work",
        "project_management_sync_change_classification",
        "project_management_complete_work",
        "project_management_schema_plan",
        "project_management_schema_status",
        "project_management_merge_readiness",
        "project_management_documentation_reconcile",
        "project_management_portfolio_status",
        "project_management_persist_review",
        "project_management_verify_traceability",
        "project_management_current_work",
        "project_management_board_data",
    }
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


class _AdapterCaller:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.responses = [
            {"project": {"id": "PVT_1", "title": "KIS Work Management", "closed": False}},
            {
                "fields": [
                    {"id": "F_STATUS", "name": "Status", "data_type": "single_select"},
                    {"id": "F_OWNER", "name": "Execution Owner", "data_type": "text"},
                ],
                "pageInfo": {"hasNextPage": False},
            },
            {
                "items": [
                    {
                        "id": "item-234",
                        "content_type": "Issue",
                        "content": {
                            "title": "Earlier item",
                            "number": 234,
                            "state": "OPEN",
                            "repository": "NielPieterse0/kis-mcp",
                        },
                        "fields": [{"name": "Status", "value": {"name": "Todo"}}],
                    },
                    {
                        "id": "item-235",
                        "content_type": "Issue",
                        "content": {
                            "title": "Fix selector",
                            "number": 235,
                            "state": "OPEN",
                            "repository": "NielPieterse0/kis-mcp",
                        },
                        "fields": [
                            {"name": "Status", "value": {"name": "Active"}},
                            {"name": "Execution Owner", "value": "agent-1"},
                        ],
                    },
                ],
                "pageInfo": {"hasNextPage": False},
            },
        ]

    async def call_tool(self, name, arguments):
        self.calls.append((name, dict(arguments)))
        return self.responses.pop(0)


class _AdapterService:
    def __init__(self) -> None:
        self.caller = _AdapterCaller()
        self.adapter = GitHubProjectInventoryAdapter(self.caller)
        self.binding = ProjectBinding(
            binding_id="github-default",
            managed_project_id="kis-mcp",
            provider_id="github-mcp",
            owner="NielPieterse0",
            owner_type=ProjectOwnerType.USER,
            project_number=1,
            repository="NielPieterse0/kis-mcp",
        )

    async def read_inventory(self, project_id, *, field_names=(), item_limit=100, query=None):
        assert project_id == "kis-mcp"
        return await self.adapter.read_inventory(
            self.binding, field_names=field_names, item_limit=item_limit, query=query
        )


def test_board_data_filters_unprovisioned_project_fields() -> None:
    server = FastMCP("root")
    service = _AdapterService()
    register_project_management_enhancement_tools(server, service)

    result = asyncio.run(
        server.call_tool(
            "project_management_board_data",
            {"project_id": "kis-mcp", "item_limit": 20},
        )
    ).structured_content

    assert result is not None
    assert result["result"]["complete"] is True
    assert [card["number"] for card in result["result"]["cards"]] == [235, 234]
    assert result["result"]["cards"][0]["work_state"] == "active"
    item_call = service.caller.calls[-1][1]
    assert item_call["field_names"] == ["Status", "Execution Owner"]
    assert "Created" not in item_call["field_names"]
    assert "Priority" not in item_call["field_names"]


def test_current_work_filters_unprovisioned_project_fields() -> None:
    server = FastMCP("root")
    service = _AdapterService()
    register_project_management_enhancement_tools(server, service)

    result = asyncio.run(
        server.call_tool(
            "project_management_current_work",
            {"project_id": "kis-mcp", "execution_owner": "agent-1", "item_limit": 20},
        )
    ).structured_content

    assert result is not None
    assert result["result"]["status"] == "current"
    assert result["result"]["selected"]["number"] == 235
    assert service.caller.calls[-1][1]["field_names"] == ["Status", "Execution Owner"]


def test_contract_exposes_canonical_work_semantics_and_fingerprints() -> None:
    server = FastMCP("root")
    service = _Service()
    register_project_management_enhancement_tools(server, service)

    result = asyncio.run(
        server.call_tool("project_management_contract", {})
    ).structured_content

    assert result is not None
    canonical = result["canonical_contracts"]
    assert set(canonical["fingerprints"]) == {
        "work_item_semantics",
        "work_lifecycle_operations",
        "work_selection",
    }
    assert all(len(value) == 64 for value in canonical["fingerprints"].values())
    fields = canonical["work_item_semantics"]["fields"]
    assert [item["name"] for item in fields if item["managed"]][-3:] == [
        "Live Verification", "Commissioning Key", "Live Verification Evidence"
    ]
    assert canonical["work_selection"]["ranking"] == [
        "priority", "effort", "created_order", "record_id"
    ]
    assert "work_class" not in canonical["work_selection"]["fields"]
    assert service.calls == []


def test_targeted_board_query_is_forwarded_before_provider_item_limit() -> None:
    server = FastMCP("root")
    service = _Service()
    register_project_management_enhancement_tools(server, service)

    result = asyncio.run(server.call_tool(
        "project_management_board_data",
        {"project_id": "kis-mcp", "query": "215", "item_limit": 20},
    )).structured_content

    assert result is not None
    assert result["result"]["cards"][0]["number"] == 215
    assert service.calls[-1][2] == 20
    assert service.calls[-1][3] == "215"


def test_github_inventory_applies_targeted_query_at_provider_boundary() -> None:
    service = _AdapterService()
    inventory = asyncio.run(service.read_inventory(
        "kis-mcp", field_names=("Status",), item_limit=20, query="235",
    ))

    assert inventory.items
    item_call = service.caller.calls[-1][1]
    assert item_call["per_page"] == 20
    assert item_call["query"] == "235"
