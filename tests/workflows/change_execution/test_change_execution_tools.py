from __future__ import annotations

import asyncio
from typing import Any

from fastmcp import FastMCP

from kis_mcp.workflows.change_execution.contracts import ChangeExecutionResult
from kis_mcp.workflows.change_execution.tools import register_change_execution_tool


class _Service:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def execute(self, **kwargs: Any) -> ChangeExecutionResult:
        self.calls.append(kwargs)
        return ChangeExecutionResult(
            project=kwargs["project"],
            source_fingerprint="a" * 64,
            complexity=kwargs.get("complexity", "medium"),
            risk_triggers=tuple(sorted(kwargs.get("risk_triggers", ()))),
            selection={"contract": "verification-selection-v1"},
            verifications=(),
            reviews=(),
            status="passed",
            verification_failed_count=0,
            verification_incomplete_count=0,
            review_error_count=0,
        )


def test_execute_change_workflow_has_bounded_process_surface() -> None:
    server = FastMCP("change-execution-test")
    service = _Service()
    register_change_execution_tool(server, service)
    tool = {item.name: item for item in asyncio.run(server.list_tools())}[
        "execute_change_workflow"
    ]
    properties = tool.parameters["properties"]
    assert set(properties) == {
        "project",
        "source",
        "commit_ref",
        "base_ref",
        "head_ref",
        "task_terms",
        "complexity",
        "risk_triggers",
        "max_verifications",
        "verification_timeout_ms",
        "review_timeout_ms",
        "review_types",
        "review_backend",
        "review_model",
        "reviewers",
        "review_rounds",
        "review_adjudication",
    }
    assert "command" not in properties
    assert "tool_name" not in properties
    assert "operation" not in properties
    assert tool.annotations.read_only_hint is False
    assert tool.annotations.destructive_hint is False

    result = asyncio.run(
        tool.run(
            {
                "project": r"C:\Projects\fixture",
                "review_types": ["architecture", "test-quality"],
            }
        )
    )
    assert result.structured_content["contract"] == "change-execution-result-v2"
    assert result.structured_content["complexity"] == "medium"
    assert result.structured_content["risk_triggers"] == []
    assert service.calls[0]["review_types"] == ("architecture", "test-quality")
