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
    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "tool": "inspect_change",
            "source": "working_tree",
            "available": True,
            "project_path": r"C:\Projects\fixture",
        }


class _Service:
    def __init__(self) -> None:
        self.requests: list[InspectChangeRequest] = []

    def inspect(self, request: InspectChangeRequest) -> _Response:
        self.requests.append(request)
        return _Response()


def _local_tools(server: FastMCP) -> list[Any]:
    return list(asyncio.run(server.local_provider.list_tools()))


def test_register_change_tools_registers_exact_tool_and_delegates() -> None:
    server = FastMCP("discover-change-registration-test")
    service = _Service()

    register_change_tools(server, service)

    tools = _local_tools(server)
    assert [tool.name for tool in tools] == ["inspect_change"]
    tool = tools[0]
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
    assert tool.annotations.readOnlyHint is True
    assert tool.annotations.destructiveHint is False
    assert tool.annotations.idempotentHint is True
    assert tool.annotations.openWorldHint is False


def test_register_change_tools_normalizes_invalid_path_without_hr_code() -> None:
    server = FastMCP("discover-change-error-test")
    register_change_tools(server, _Service())
    tool = _local_tools(server)[0]

    with pytest.raises(ToolError) as raised:
        asyncio.run(tool.run({"path": "  "}))

    payload = json.loads(str(raised.value))
    assert payload == {
        "code": "DISCOVER_CHANGE_REQUEST_INVALID",
        "message": "The inspect_change request is invalid.",
        "reason": "inspect change path must be a non-empty string",
        "field": "path",
        "corrective_actions": [
            r"Provide a non-empty local project path beneath C:\Projects."
        ],
        "retryable": False,
    }
    assert "HR-" not in str(raised.value)


def test_build_server_mounts_inspect_change_additively() -> None:
    config = RuntimeConfig(
        raw_settings=deepcopy(CONFIG.raw_settings),
        raw_policy=deepcopy(CONFIG.raw_policy),
    )

    server = build_server(config, validate_provider=False)
    names = {tool.name for tool in asyncio.run(server.list_tools())}

    assert "inspect_project" in names
    assert "inspect_change" in names
    assert "kis_health" in names
