from __future__ import annotations

import asyncio
from typing import Any

from fastmcp import FastMCP

from kis_mcp.discover.planning_contracts import PlanChangeRequest
from kis_mcp.discover.tools import register_plan_change_tool


class _Response:
    def to_json_dict(self) -> dict[str, Any]:
        return {"schema_version": 1, "tool": "plan_change", "execution_performed": False}


class _Service:
    def __init__(self) -> None:
        self.requests: list[PlanChangeRequest] = []

    def plan(self, request: PlanChangeRequest) -> _Response:
        self.requests.append(request)
        return _Response()


def test_plan_change_tool_is_read_only_and_preserves_request_shape() -> None:
    server = FastMCP("plan-change-test")
    service = _Service()
    register_plan_change_tool(server, service)

    tools = {tool.name: tool for tool in asyncio.run(server.list_tools())}
    tool = tools["plan_change"]
    assert tool.annotations.readOnlyHint is True
    assert "command" not in tool.parameters["properties"]
    result = asyncio.run(
        tool.run(
            {
                "project": r"C:\Projects\fixture",
                "task": "verify current change",
                "source": "working_tree",
                "max_chars": 12_000,
                "max_files": 8,
                "max_symbols": 20,
                "max_relationships": 20,
                "max_dependants": 30,
                "max_tests": 30,
                "max_verifications": 10,
            }
        )
    )

    assert result.structured_content == {
        "schema_version": 1,
        "tool": "plan_change",
        "execution_performed": False,
    }
    assert service.requests == [
        PlanChangeRequest(
            project=r"C:\Projects\fixture",
            task="verify current change",
            max_chars=12_000,
            max_files=8,
            max_symbols=20,
            max_relationships=20,
            max_dependants=30,
            max_tests=30,
            max_verifications=10,
        )
    ]


def test_plan_change_is_discoverable_as_change_planning_capability() -> None:
    from kis_mcp.discover.platform import discover_capability_contributions

    operations = {
        operation.name: operation
        for contribution in discover_capability_contributions()
        for operation in contribution.operations
    }

    assert "plan_change" in operations
    assert operations["plan_change"].effects[0].value == "read_only"
    assert "code.change.plan" in operations["plan_change"].capabilities
