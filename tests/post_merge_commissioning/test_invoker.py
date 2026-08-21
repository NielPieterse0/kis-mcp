from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import mcp.types as mcp_types
from fastmcp import FastMCP
from fastmcp.tools.tool import ToolResult

from kis_mcp.commissioning_runtime.invoker import CommissioningFastMCPInvoker


class FakeServer:
    def __init__(self, result: ToolResult, resource: Any = None) -> None:
        self.result = result
        self.resource = resource
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.resource_reads: list[str] = []

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        self.calls.append((name, dict(arguments)))
        return self.result

    async def read_resource(self, uri: str) -> Any:
        self.resource_reads.append(uri)
        return self.resource


def _text(value: str) -> mcp_types.TextContent:
    return mcp_types.TextContent(type="text", text=value)


def test_json_text_envelope_is_decoded() -> None:
    server = FakeServer(ToolResult(content=[_text('{"number":452,"merged":true}')]))
    invoker = CommissioningFastMCPInvoker(server)

    result = asyncio.run(invoker.external("github_pull_request_read", {"pullNumber": 452}))

    assert result == {"number": 452, "merged": True}
    assert server.calls == [
        (
            "execute_external_action",
            {
                "operation": "github_pull_request_read",
                "arguments": {"pullNumber": 452},
            },
        )
    ]


def test_embedded_text_resource_is_returned_as_content() -> None:
    embedded = mcp_types.EmbeddedResource(
        type="resource",
        resource=mcp_types.TextResourceContents(
            uri="file:///scope.json",
            mimeType="application/json",
            text='{"schema_version":4}',
        ),
    )
    invoker = CommissioningFastMCPInvoker(FakeServer(ToolResult(content=[embedded])))

    assert asyncio.run(invoker.external("github_get_file_contents", {})) == {
        "content": '{"schema_version":4}'
    }


def test_resource_link_is_preferred_over_informational_text() -> None:
    link = mcp_types.ResourceLink(
        type="resource_link",
        name="scope.json",
        uri="file:///scope.json",
        mimeType="application/json",
    )
    resource = SimpleNamespace(
        contents=[
            mcp_types.TextResourceContents(
                uri="file:///scope.json",
                mimeType="application/json",
                text='{"schema_version":4}',
            )
        ]
    )
    server = FakeServer(
        ToolResult(content=[_text("successfully downloaded text file"), link]),
        resource=resource,
    )
    invoker = CommissioningFastMCPInvoker(server)

    result = asyncio.run(invoker.external("github_get_file_contents", {}))

    assert result == {"content": '{"schema_version":4}'}
    assert server.resource_reads == ["file:///scope.json"]


def test_result_budget_envelope_is_rejected_without_replay() -> None:
    envelope = {
        "truncated": True,
        "reason": "RESULT_BUDGET_EXCEEDED",
        "operation": "github_issue_write",
        "original_chars": 1000,
        "max_chars": 100,
        "preview": {},
    }
    server = FakeServer(ToolResult(structured_content=envelope))
    invoker = CommissioningFastMCPInvoker(server)

    try:
        asyncio.run(invoker.external("github_issue_write", {}))
    except RuntimeError as exc:
        assert "RESULT_BUDGET_EXCEEDED" in str(exc)
    else:
        raise AssertionError("budget envelope should fail closed")
    assert len(server.calls) == 1


def test_real_fastmcp_nested_dispatch_preserves_dict_and_list_payloads() -> None:
    server = FastMCP("commissioning-invoker-nested-test")

    @server.tool(name="provider_dict")
    def provider_dict() -> dict[str, Any]:
        return {"number": 452, "merged": True}

    @server.tool(name="provider_list")
    def provider_list() -> list[dict[str, Any]]:
        return [{"sha": "b" * 40}]

    @server.tool(name="execute_external_action")
    async def execute_external_action(operation: str, arguments: dict[str, Any]) -> Any:
        return await server.call_tool(operation, arguments)

    invoker = CommissioningFastMCPInvoker(server)

    assert asyncio.run(invoker.external("provider_dict", {})) == {
        "number": 452,
        "merged": True,
    }
    assert asyncio.run(invoker.external("provider_list", {})) == [{"sha": "b" * 40}]


def test_fastmcp_tool_error_is_normalized_to_runtime_failure() -> None:
    from fastmcp.exceptions import ToolError

    class RaisingServer:
        async def call_tool(self, _name: str, _arguments: dict[str, Any]) -> ToolResult:
            raise ToolError("provider detail must not escape receipt handling")

    invoker = CommissioningFastMCPInvoker(RaisingServer())

    try:
        asyncio.run(invoker.external("github_pull_request_read", {}))
    except RuntimeError as exc:
        assert str(exc) == "github_pull_request_read provider call failed"
    else:
        raise AssertionError("FastMCP provider errors must be normalized")


def test_read_and_change_dispatch_use_exact_kis_control_planes() -> None:
    read_server = FakeServer(ToolResult(content=[_text('{"schema_version":1,"ready":true}')]))
    read_invoker = CommissioningFastMCPInvoker(read_server)
    assert asyncio.run(read_invoker.read("kis_health", {}))["ready"] is True
    assert read_server.calls == [
        ("execute_read_action", {"operation": "kis_health", "arguments": {}})
    ]

    change_server = FakeServer(ToolResult(content=[_text('{"mode":"apply"}')]))
    change_invoker = CommissioningFastMCPInvoker(change_server)
    assert asyncio.run(
        change_invoker.change(
            "project_management_transition_work", {"issue_number": 460}
        )
    ) == {"mode": "apply"}
    assert change_server.calls == [
        (
            "execute_change_action",
            {
                "operation": "project_management_transition_work",
                "arguments": {"issue_number": 460},
            },
        )
    ]
