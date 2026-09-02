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
from kis_mcp.discover.context_contracts import (
    CodeContextBudget,
    GetCodeContextRequest,
)
from kis_mcp.discover.contracts import InspectProjectRequest
from kis_mcp.discover.errors import DiscoverError
from kis_mcp.server import build_server
from kis_mcp.skills import SKILLS_TOOL_NAMES

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CONFIG = load_runtime_config(REPOSITORY_ROOT)


class _ProjectResponse:
    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "tool": "inspect_project",
            "project": {"project_id": "fixture"},
        }


class _ContextResponse:
    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "tool": "get_code_context",
            "project": {"project_id": "fixture"},
            "task": "review authentication",
        }


class _Service:
    def __init__(self) -> None:
        self.project_requests: list[InspectProjectRequest] = []
        self.context_requests: list[GetCodeContextRequest] = []

    def inspect(self, request: InspectProjectRequest) -> _ProjectResponse:
        self.project_requests.append(request)
        return _ProjectResponse()

    def get_code_context(self, request: GetCodeContextRequest) -> _ContextResponse:
        self.context_requests.append(request)
        return _ContextResponse()


class _FailingService(_Service):
    def inspect(self, request: InspectProjectRequest) -> _ProjectResponse:
        raise DiscoverError(
            code="DISCOVER_PATH_INVALID",
            message="The project path is invalid.",
            reason=f"Rejected {request.path}.",
            field="path",
            corrective_actions=("Choose a directory beneath C:\\Projects.",),
        )

    def get_code_context(self, request: GetCodeContextRequest) -> _ContextResponse:
        raise DiscoverError(
            code="DISCOVER_CONTEXT_UNAVAILABLE",
            message="The requested context is unavailable.",
            reason=f"Rejected task {request.task}.",
            field="task",
            corrective_actions=("Provide a supported bounded task.",),
        )


def _local_tools(server: FastMCP) -> list[Any]:
    return list(asyncio.run(server.local_provider.list_tools()))


def _tool(server: FastMCP, name: str) -> Any:
    return next(item for item in _local_tools(server) if item.name == name)


def test_inspect_project_service_delegates_context_with_shared_boundary_and_settings(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from kis_mcp.discover import service as service_module
    from kis_mcp.discover.service import InspectProjectService

    settings = object()
    response = object()
    request = GetCodeContextRequest(
        project=str(tmp_path),
        task="review authentication",
        budget=CodeContextBudget(8_000, 6, 12, 10),
    )
    captured: dict[str, Any] = {}

    class _Broker:
        def __init__(self, *, boundary: Path, settings: object) -> None:
            captured["boundary"] = boundary
            captured["settings"] = settings

        def get(self, received: GetCodeContextRequest) -> object:
            captured["request"] = received
            return response

    monkeypatch.setattr(service_module, "ContextBrokerService", _Broker)

    actual = InspectProjectService(
        boundary=tmp_path,
        settings=settings,  # type: ignore[arg-type]
    ).get_code_context(request)

    assert actual is response
    assert captured == {
        "boundary": tmp_path,
        "settings": settings,
        "request": request,
    }


def test_register_discover_tools_registers_exact_public_surface_and_delegates() -> None:
    from kis_mcp.discover.tools import register_discover_tools

    server = FastMCP("discover-registration-test")
    service = _Service()

    register_discover_tools(server, service)

    tools = _local_tools(server)
    assert [tool.name for tool in tools] == ["inspect_project", "get_code_context"]
    project_result = asyncio.run(
        _tool(server, "inspect_project").run(
            {
                "path": r"C:\Projects\fixture",
                "limits": {"max_files": 10},
            }
        )
    )
    context_result = asyncio.run(
        _tool(server, "get_code_context").run(
            {
                "project": r"C:\Projects\fixture",
                "task": "review authentication",
                "max_chars": 8_000,
                "max_files": 6,
                "max_symbols": 12,
                "max_relationships": 10,
            }
        )
    )

    assert project_result.structured_content == {
        "schema_version": 1,
        "tool": "inspect_project",
        "project": {"project_id": "fixture"},
    }
    assert context_result.structured_content == {
        "schema_version": 1,
        "tool": "get_code_context",
        "project": {"project_id": "fixture"},
        "task": "review authentication",
    }
    assert service.project_requests == [
        InspectProjectRequest(
            path=r"C:\Projects\fixture",
            limits={"max_files": 10},
        )
    ]
    assert service.context_requests == [
        GetCodeContextRequest(
            project=r"C:\Projects\fixture",
            task="review authentication",
            budget=CodeContextBudget(
                max_chars=8_000,
                max_files=6,
                max_symbols=12,
                max_relationships=10,
            ),
        )
    ]
    for tool in tools:
        assert tool.annotations is not None
        assert tool.annotations.read_only_hint is True
        assert tool.annotations.destructive_hint is False
        assert tool.annotations.idempotent_hint is True
        assert tool.annotations.open_world_hint is False


def test_register_discover_tools_normalizes_structural_errors_without_hr_codes() -> None:
    from kis_mcp.discover.tools import register_discover_tools

    server = FastMCP("discover-error-test")
    register_discover_tools(server, _FailingService())

    with pytest.raises(ToolError) as raised:
        asyncio.run(
            _tool(server, "inspect_project").run(
                {"path": r"C:\Projects\fixture", "limits": None}
            )
        )
    project_payload = json.loads(str(raised.value))
    assert project_payload["code"] == "DISCOVER_PATH_INVALID"
    assert project_payload["field"] == "path"
    assert project_payload["retryable"] is False
    assert "HR-" not in str(raised.value)

    with pytest.raises(ToolError) as raised:
        asyncio.run(
            _tool(server, "get_code_context").run(
                {
                    "project": r"C:\Projects\fixture",
                    "task": "review authentication",
                    "max_chars": 8_000,
                    "max_files": 6,
                    "max_symbols": 12,
                    "max_relationships": 10,
                }
            )
        )
    context_payload = json.loads(str(raised.value))
    assert context_payload["code"] == "DISCOVER_CONTEXT_UNAVAILABLE"
    assert context_payload["field"] == "task"
    assert context_payload["retryable"] is False
    assert "HR-" not in str(raised.value)


def test_get_code_context_normalizes_invalid_request_contract() -> None:
    from kis_mcp.discover.tools import register_discover_tools

    server = FastMCP("discover-context-request-error-test")
    register_discover_tools(server, _Service())

    with pytest.raises(ToolError) as raised:
        asyncio.run(
            _tool(server, "get_code_context").run(
                {
                    "project": r"C:\Projects\fixture",
                    "task": " ",
                    "max_chars": 1_000,
                    "max_files": 0,
                    "max_symbols": 0,
                    "max_relationships": 0,
                }
            )
        )

    payload = json.loads(str(raised.value))
    assert payload["code"] == "DISCOVER_CONTEXT_REQUEST_INVALID"
    assert payload["field"] == "request"
    assert payload["retryable"] is False
    assert "HR-" not in str(raised.value)


def test_build_server_adds_context_without_changing_existing_local_tools() -> None:
    settings = deepcopy(CONFIG.raw_settings)
    config = RuntimeConfig(raw_settings=settings, raw_policy=deepcopy(CONFIG.raw_policy))

    server = build_server(config, validate_provider=False)
    names = {tool.name for tool in _local_tools(server)}

    assert names == {
        "inspect_project",
        "get_code_context",
        "plan_change",
        "run_verification",
        "select_change_verification",
        "execute_change_workflow",
        "change_lifecycle_decision",
        "prepare_reviewable_pull_request",
        "materialize_task_handoff",
        "get_task_handoff",
        "candidate_endpoint_status",
        "start_task_candidate",
        "candidate_identity",
        "workflow_terminal_audit",
        "verify_task_candidate",
        "stop_task_candidate",
        "derive_promotion_ready",
        "converge_change_to_done",
        "validate_agent_configuration",
        "kis_health",
        "kis_housekeeping_status",
        "kis_housekeeping_receipt",
        "kis_housekeeping_apply_receipt",
        "kis_post_merge_commissioning_status",
        "kis_post_merge_commissioning_receipt",
        "kis_post_merge_commissioning_execution",
        "kis_post_merge_commissioning_run",
        "commission_mcp_extension",
        "mcp_extension_commissioning_status",
        "kis_list_projects",
        "kis_project_status",
        "kis_list_quarantine",
        "kis_quarantine_path",
        "kis_restore_quarantine",
        "search_capabilities",
        "describe_capability",
        "recommend_workflow",
        "execute_read_action",
        "execute_change_action",
        "execute_external_action",
        *SKILLS_TOOL_NAMES,
    }
