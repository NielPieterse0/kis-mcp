from __future__ import annotations

import asyncio

from fastmcp import FastMCP
from fastmcp.tools import ToolResult
from jsonschema import Draft202012Validator
from mcp import types as mcp_types

from kis_mcp.mcp2026_prompts import (
    DeterministicDiscoveryTransform,
    register_mcp2026_workflow_prompts,
)


def test_fastmcp4_sdk_surface_is_snake_case_while_mcp_wire_uses_aliases() -> None:
    server = FastMCP("mcp2026-wire")

    @server.tool(annotations={"read_only_hint": True})
    def echo(value: str) -> dict[str, str]:
        return {"value": value}

    tool = asyncio.run(server.get_tool("echo"))
    assert tool.annotations.read_only_hint is True
    assert "value" in tool.parameters["properties"]

    wire = tool.to_mcp_tool().model_dump(by_alias=True, exclude_none=True)
    assert "inputSchema" in wire
    assert "outputSchema" in wire
    assert wire["annotations"]["readOnlyHint"] is True


def test_generated_tool_schemas_are_valid_under_default_json_schema_2020_12() -> None:
    server = FastMCP("mcp2026-schema")

    @server.tool
    def calculate(a: int, b: int) -> dict[str, int]:
        return {"sum": a + b}

    tool = asyncio.run(server.get_tool("calculate"))
    wire = tool.to_mcp_tool()
    assert "$schema" not in wire.input_schema
    Draft202012Validator.check_schema(wire.input_schema)
    assert wire.output_schema is not None
    Draft202012Validator.check_schema(wire.output_schema)


def test_resource_link_is_accepted_as_modern_tool_content() -> None:
    server = FastMCP("mcp2026-resource-link")

    @server.tool
    def linked_source() -> ToolResult:
        return ToolResult(content=[mcp_types.ResourceLink(
            name="source.py",
            uri="file:///project/source.py",
            mimeType="text/x-python",
        )])

    result = asyncio.run(server.call_tool("linked_source", {}))
    assert result.is_error is False
    assert len(result.content) == 1
    link = result.content[0]
    assert isinstance(link, mcp_types.ResourceLink)
    assert link.type == "resource_link"
    assert str(link.uri) == "file:///project/source.py"


def test_mcp2026_workflow_prompts_are_thin_user_invoked_entry_points() -> None:
    server = FastMCP("mcp2026-prompts")
    server.add_transform(DeterministicDiscoveryTransform())
    register_mcp2026_workflow_prompts(server)

    async def run() -> None:
        prompts = await server.list_prompts()
        assert [prompt.name for prompt in prompts] == [
            "explain-change",
            "resume-change",
            "start-change",
            "take-next-work",
        ]

        rendered = await server.render_prompt(
            "take-next-work",
            {"project_id": "kis-mcp", "execution_owner": "agent-c"},
        )
        text = "\n".join(str(message.content) for message in rendered.messages)
        assert "project_management_take_next_work" in text
        assert "Work Management remains authoritative" in text
        assert "agent-c" in text

    asyncio.run(run())


def test_pinned_sdk_supports_2026_cacheable_list_result_contract() -> None:
    expected = {"ttl_ms", "cache_scope", "result_type"}
    assert expected <= set(mcp_types.ListToolsResult.model_fields)
    assert expected <= set(mcp_types.ListPromptsResult.model_fields)
    assert expected <= set(mcp_types.ListResourcesResult.model_fields)


def test_discovery_transform_orders_tools_and_resources_deterministically() -> None:
    server = FastMCP("mcp2026-discovery-order")
    server.add_transform(DeterministicDiscoveryTransform())

    @server.tool(name="zeta")
    def zeta() -> str:
        return "z"

    @server.tool(name="alpha")
    def alpha() -> str:
        return "a"

    @server.resource("file:///zeta")
    def zeta_resource() -> str:
        return "z"

    @server.resource("file:///alpha")
    def alpha_resource() -> str:
        return "a"

    async def run() -> None:
        assert [tool.name for tool in await server.list_tools()] == ["alpha", "zeta"]
        assert [str(resource.uri) for resource in await server.list_resources()] == [
            "file:///alpha",
            "file:///zeta",
        ]

    asyncio.run(run())
