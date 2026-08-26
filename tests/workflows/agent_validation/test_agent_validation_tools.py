from __future__ import annotations

import asyncio
from typing import Any

import pytest
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from kis_mcp.workflows.agent_validation.contracts import AgentValidationResult
from kis_mcp.workflows.agent_validation.execution import AgentValidationError
from kis_mcp.workflows.agent_validation.tools import register_agent_validation_tool


class _Service:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[dict[str, Any]] = []

    async def validate(self, **kwargs: Any) -> AgentValidationResult:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return AgentValidationResult(
            project=kwargs["project"], target=kwargs["target"], strict=kwargs["strict"],
            max_files=kwargs["max_files"] or 100, version="0.45.0", files_checked=1,
            diagnostics=(), errors=0, warnings=0, info=0,
        )


def test_tool_surface_has_no_free_form_fix_or_command_inputs() -> None:
    server = FastMCP("agnix-tool-test")
    service = _Service()
    register_agent_validation_tool(server, service)
    tool = {item.name: item for item in asyncio.run(server.list_tools())}[
        "validate_agent_configuration"
    ]
    properties = tool.parameters["properties"]
    assert set(properties) == {"project", "target", "strict", "max_files"}
    assert "arguments" not in properties
    assert "fix" not in properties
    assert "command" not in properties
    assert tool.annotations.destructive_hint is False


def test_structural_errors_are_not_hr_policy_codes() -> None:
    server = FastMCP("agnix-error-test")
    register_agent_validation_tool(
        server,
        _Service(error=AgentValidationError("AGNIX_TARGET_INVALID", "bad target")),
    )
    tool = {item.name: item for item in asyncio.run(server.list_tools())}[
        "validate_agent_configuration"
    ]
    with pytest.raises(ToolError) as raised:
        asyncio.run(tool.run({"project": r"C:\Projects\fixture", "target": "other"}))
    assert "AGNIX_TARGET_INVALID" in str(raised.value)
    assert "HR-" not in str(raised.value)
