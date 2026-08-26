from __future__ import annotations

import asyncio
from typing import Any

from fastmcp import FastMCP

from kis_mcp.discover.change_analysis import AnalyzeChangeRequest
from kis_mcp.discover.tools import register_analyze_change_tool


class _Response:
    def to_json_dict(self) -> dict[str, Any]:
        return {"schema_version": 1, "tool": "analyze_change", "normalized_change": {"changed_paths": ["src/app.py"]}}


class _Service:
    def __init__(self) -> None:
        self.requests: list[AnalyzeChangeRequest] = []

    def analyze(self, request: AnalyzeChangeRequest) -> _Response:
        self.requests.append(request)
        return _Response()


def test_register_analyze_change_tool_delegates_bounded_request() -> None:
    server = FastMCP("analyze-change-tool-test")
    service = _Service()
    register_analyze_change_tool(server, service)
    tool = list(asyncio.run(server.local_provider.list_tools()))[0]

    result = asyncio.run(
        tool.run(
            {
                "project": r"C:\Projects\fixture",
                "source": "supplied",
                "task_terms": ["auth"],
                "supplied_changes": [{"path": "src/app.py", "status": "modified"}],
                "github_context": {
                    "repository": "owner/repo",
                    "pull_number": 3,
                    "base_sha": "a" * 40,
                    "head_sha": "b" * 40,
                    "changes": [],
                },
                "max_symbols": 10,
                "max_dependants": 10,
                "max_tests": 10,
                "max_verifications": 10,
            }
        )
    )

    assert tool.name == "analyze_change"
    assert tool.annotations.read_only_hint is True
    assert result.structured_content["tool"] == "analyze_change"
    assert service.requests[0].task_terms == ("auth",)
    assert service.requests[0].supplied_changes[0].path == "src/app.py"
