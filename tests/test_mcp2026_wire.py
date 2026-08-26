from __future__ import annotations

import asyncio

from fastmcp import FastMCP
from fastmcp.tools import ToolResult
from jsonschema import Draft202012Validator
from mcp import types as mcp_types


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
