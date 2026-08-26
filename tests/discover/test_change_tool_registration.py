from __future__ import annotations

import asyncio
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from kis_mcp.config import RuntimeConfig, load_runtime_config
from kis_mcp.discover.change_inspection_contracts import InspectChangeRequest
from kis_mcp.discover.tools import register_change_tools
from kis_mcp.server import build_server

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CONFIG = load_runtime_config(REPOSITORY_ROOT)


class _Response:
    def __init__(self, source: str) -> None:
        self.source = source

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "tool": "inspect_change",
            "source": self.source,
            "available": True,
            "project_path": r"C:\Projects\fixture",
        }


class _Service:
    def __init__(self) -> None:
        self.requests: list[InspectChangeRequest] = []

    def inspect(self, request: InspectChangeRequest) -> _Response:
        self.requests.append(request)
        return _Response(request.source)


def _local_tools(server: FastMCP) -> list[Any]:
    return list(asyncio.run(server.local_provider.list_tools()))


def test_register_change_tools_registers_exact_tool_and_preserves_default() -> None:
    server = FastMCP("discover-change-registration-test")
    service = _Service()

    register_change_tools(server, service)

    tools = _local_tools(server)
    assert [tool.name for tool in tools] == ["inspect_change", "build_review_map"]
    tool = next(item for item in tools if item.name == "inspect_change")
    result = asyncio.run(tool.run({"path": r"C:\Projects\fixture"}))

    assert result.structured_content == {
        "schema_version": 1,
        "tool": "inspect_change",
        "source": "working_tree",
        "available": True,
        "project_path": r"C:\Projects\fixture",
    }
    assert service.requests == [InspectChangeRequest(path=r"C:\Projects\fixture")]
    assert tool.annotations is not None
    assert tool.annotations.read_only_hint is True
    assert tool.annotations.destructive_hint is False
    assert tool.annotations.idempotent_hint is True
    assert tool.annotations.open_world_hint is False


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        (
            {"path": r"C:\Projects\fixture", "source": "staged"},
            InspectChangeRequest(path=r"C:\Projects\fixture", source="staged"),
        ),
        (
            {
                "path": r"C:\Projects\fixture",
                "source": "commit",
                "commit_ref": "abc123",
            },
            InspectChangeRequest(
                path=r"C:\Projects\fixture",
                source="commit",
                commit_ref="abc123",
            ),
        ),
        (
            {
                "path": r"C:\Projects\fixture",
                "source": "range",
                "base_ref": "main",
                "head_ref": "feature/test",
            },
            InspectChangeRequest(
                path=r"C:\Projects\fixture",
                source="range",
                base_ref="main",
                head_ref="feature/test",
            ),
        ),
        (
            {
                "path": r"C:\Projects\fixture",
                "source": "branch",
                "base_ref": "main",
                "head_ref": "feature/test",
            },
            InspectChangeRequest(
                path=r"C:\Projects\fixture",
                source="branch",
                base_ref="main",
                head_ref="feature/test",
            ),
        ),
    ],
)
def test_register_change_tools_delegates_all_supported_target_shapes(
    arguments: dict[str, Any],
    expected: InspectChangeRequest,
) -> None:
    server = FastMCP("discover-change-target-test")
    service = _Service()
    register_change_tools(server, service)
    tool = _local_tools(server)[0]

    result = asyncio.run(tool.run(arguments))

    assert result.structured_content["source"] == expected.source
    assert service.requests == [expected]


@pytest.mark.parametrize(
    ("arguments", "field"),
    [
        ({"path": "  "}, "path"),
        (
            {"path": r"C:\Projects\fixture", "source": "unsupported"},
            "source",
        ),
        (
            {
                "path": r"C:\Projects\fixture",
                "source": "commit",
                "commit_ref": "--unsafe",
            },
            "commit_ref",
        ),
        (
            {
                "path": r"C:\Projects\fixture",
                "source": "range",
                "base_ref": "main",
            },
            "request",
        ),
    ],
)
def test_register_change_tools_normalizes_invalid_request_without_hr_code(
    arguments: dict[str, Any],
    field: str,
) -> None:
    server = FastMCP("discover-change-error-test")
    register_change_tools(server, _Service())
    tool = _local_tools(server)[0]

    with pytest.raises(ToolError) as raised:
        asyncio.run(tool.run(arguments))

    payload = json.loads(str(raised.value))
    assert payload["code"] == "DISCOVER_CHANGE_REQUEST_INVALID"
    assert payload["field"] == field
    assert payload["retryable"] is False
    assert "HR-" not in str(raised.value)


def test_build_server_mounts_three_discover_operations_additively() -> None:
    config = RuntimeConfig(
        raw_settings=deepcopy(CONFIG.raw_settings),
        raw_policy=deepcopy(CONFIG.raw_policy),
    )

    server = build_server(config, validate_provider=False)
    names = {tool.name for tool in asyncio.run(server.list_tools())}

    assert {"inspect_project", "inspect_change", "kis_health"}.issubset(names)
    assert "get_code_context" not in names
    assert "analyze_change" not in names
    assert "inspect_provider_candidate" not in names
    assert "inspect_project_catalog" not in names

    context_tool = asyncio.run(server.call_tool(
        "get_code_context",
        {
            "project": str(REPOSITORY_ROOT),
            "task": "review the change",
            "max_chars": 20000,
            "max_files": 5,
            "max_symbols": 5,
            "max_relationships": 5,
        },
    ))
    assert context_tool.structured_content is not None


def test_build_server_executes_public_commit_change_target() -> None:
    config = RuntimeConfig(
        raw_settings=deepcopy(CONFIG.raw_settings),
        raw_policy=deepcopy(CONFIG.raw_policy),
    )
    server = build_server(config, validate_provider=False)

    result = asyncio.run(
        server.call_tool(
            "inspect_change",
            {
                "path": str(REPOSITORY_ROOT),
                "source": "commit",
                "commit_ref": "HEAD",
            },
        )
    )

    assert result.structured_content is not None
    assert result.structured_content["available"] is True
    assert result.structured_content["source"] == "commit"
    assert all(
        item.get("code") != "CHANGE_TARGET_READER_UNAVAILABLE"
        for item in result.structured_content["diagnostics"]
    )
