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
from kis_mcp.discover.contracts import InspectProjectRequest
from kis_mcp.discover.errors import DiscoverError
from kis_mcp.server import build_server


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CONFIG = load_runtime_config(REPOSITORY_ROOT)


class _Response:
    def to_json_dict(self) -> dict[str, Any]:
        return {"schema_version": 1, "tool": "inspect_project", "project": {"project_id": "fixture"}}


class _Service:
    def __init__(self) -> None:
        self.requests: list[InspectProjectRequest] = []

    def inspect(self, request: InspectProjectRequest) -> _Response:
        self.requests.append(request)
        return _Response()


class _FailingService:
    def inspect(self, request: InspectProjectRequest) -> _Response:
        raise DiscoverError(
            code="DISCOVER_PATH_INVALID",
            message="The project path is invalid.",
            reason=f"Rejected {request.path}.",
            field="path",
            corrective_actions=("Choose a directory beneath C:\\Projects.",),
        )


def _local_tools(server: FastMCP) -> list[Any]:
    return list(asyncio.run(server.local_provider.list_tools()))


def test_register_discover_tools_registers_exactly_one_tool_and_delegates() -> None:
    from kis_mcp.discover.tools import register_discover_tools

    server = FastMCP("discover-registration-test")
    service = _Service()

    register_discover_tools(server, service)

    tools = _local_tools(server)
    assert [tool.name for tool in tools] == ["inspect_project"]
    result = asyncio.run(
        tools[0].run(
            {
                "path": r"C:\Projects\fixture",
                "limits": {"max_files": 10},
            }
        )
    )

    assert result.structured_content == {
        "schema_version": 1,
        "tool": "inspect_project",
        "project": {"project_id": "fixture"},
    }
    assert service.requests == [
        InspectProjectRequest(
            path=r"C:\Projects\fixture",
            limits={"max_files": 10},
        )
    ]


def test_register_discover_tools_normalizes_structural_errors_without_hr_codes() -> None:
    from kis_mcp.discover.tools import register_discover_tools

    server = FastMCP("discover-error-test")
    register_discover_tools(server, _FailingService())
    tool = _local_tools(server)[0]

    with pytest.raises(ToolError) as raised:
        asyncio.run(tool.run({"path": r"C:\Outside", "limits": None}))

    payload = json.loads(str(raised.value))
    assert payload["code"] == "DISCOVER_PATH_INVALID"
    assert payload["field"] == "path"
    assert payload["retryable"] is False
    assert "HR-" not in str(raised.value)


def test_build_server_adds_discover_without_changing_existing_local_tools() -> None:
    settings = deepcopy(CONFIG.raw_settings)
    config = RuntimeConfig(raw_settings=settings, raw_policy=deepcopy(CONFIG.raw_policy))

    server = build_server(config, validate_provider=False)
    names = {tool.name for tool in _local_tools(server)}

    assert names == {
        "inspect_project",
        "kis_health",
        "kis_list_quarantine",
        "kis_quarantine_path",
        "kis_restore_quarantine",
    }
