from __future__ import annotations

import asyncio

from fastmcp import FastMCP

from kis_mcp.workflows.project_management.triage_tools import (
    register_project_management_triage_tool,
)


class Service:
    async def progress_triage(self, project_id, repository, issue_number, issue_body, **kwargs):
        return {
            "project_id": project_id,
            "repository": repository,
            "issue_number": issue_number,
            "issue_body": issue_body,
            "mode": "apply" if kwargs.get("apply") else "preview",
            "previous_fingerprint": kwargs.get("previous_fingerprint"),
            "idempotency_key": kwargs.get("idempotency_key"),
        }


def test_triage_tool_is_bounded_and_preview_by_default() -> None:
    server = FastMCP("root")
    register_project_management_triage_tool(server, Service())
    tools = {tool.name: tool for tool in asyncio.run(server.list_tools())}
    assert set(tools) == {"project_management_progress_triage"}
    annotations = tools["project_management_progress_triage"].annotations
    assert annotations is not None
    assert annotations.read_only_hint is False
    assert annotations.idempotent_hint is True


def test_triage_tool_forwards_fingerprint_and_apply_identity() -> None:
    server = FastMCP("root")
    register_project_management_triage_tool(server, Service())
    result = asyncio.run(
        server.call_tool(
            "project_management_progress_triage",
            {
                "project_id": "kis-mcp",
                "repository": "NielPieterse0/kis-mcp",
                "issue_number": 543,
                "issue_body": "## Outcome\nValid\n\n## Acceptance criteria\nComplete",
                "previous_fingerprint": "abc123",
                "apply": True,
                "idempotency_key": "triage-543",
            },
        )
    ).structured_content
    assert result is not None
    assert result["mode"] == "apply"
    assert result["previous_fingerprint"] == "abc123"
    assert result["idempotency_key"] == "triage-543"
