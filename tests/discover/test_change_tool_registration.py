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
from kis_mcp.discover.change_inspection_contracts import (
    ChangedFile,
    ChangeIdentity,
    ChangeImpactSummary,
    InspectChangeRequest,
    InspectChangeResponse,
)
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


class _ReviewMapService:
    def inspect(self, request: InspectChangeRequest) -> InspectChangeResponse:
        changed = ChangedFile(
            path="src/pkg/a.py",
            previous_path=None,
            staged_status=None,
            worktree_status="modified",
            untracked=False,
            categories=("source",),
        )
        return InspectChangeResponse(
            available=True,
            project_path=request.path,
            repository_root=request.path,
            change=ChangeIdentity(source=request.source, fingerprint="a" * 64),
            changed_files=(changed,),
            affected_scopes=("src",),
            changed_tests=(),
            contract_paths=(),
            documentation_paths=(),
            configuration_paths=(),
            policy_paths=(),
            impact_summary=ChangeImpactSummary(
                total_files=1,
                source_files=1,
                test_files=0,
                contract_files=0,
                documentation_files=0,
                configuration_files=0,
                policy_files=0,
                other_files=0,
            ),
            diagnostics=(),
            unknowns=(),
            confidence="high",
            truncated=False,
            source=request.source,
        )


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


def test_build_review_map_public_success_contract_is_literal() -> None:
    server = FastMCP("discover-review-map-success-test")
    register_change_tools(server, _ReviewMapService())
    tool = next(item for item in _local_tools(server) if item.name == "build_review_map")

    result = asyncio.run(tool.run({"path": r"C:\Projects\fixture"}))
    payload = result.structured_content

    assert payload is not None
    assert set(payload) == {
        "schema_version",
        "tool",
        "authority",
        "source",
        "source_fingerprint",
        "source_identity",
        "sections",
        "relationships",
        "omitted_relationship_count",
        "included_files",
        "omitted_files",
        "progress",
        "truncated",
        "incomplete",
        "unknowns",
        "diagnostics",
        "gate_authority",
    }
    assert payload["tool"] == "build_review_map"
    assert payload["source_fingerprint"] == "a" * 64
    assert payload["included_files"] == ["src/pkg/a.py"]
    assert payload["relationships"] == [
        {"kind": "affected_scope", "source": "src", "targets": ["src/pkg/a.py"]}
    ]
    assert payload["gate_authority"] == {
        "review": False,
        "verification": False,
        "merge_readiness": False,
        "mutation": False,
    }


@pytest.mark.parametrize(
    ("arguments", "reason"),
    [
        (
            {
                "path": r"C:\Projects\fixture",
                "expected_source_fingerprint": "b" * 64,
            },
            "review map source fingerprint is stale",
        ),
        (
            {"path": r"C:\Projects\fixture", "max_files": 0},
            "max_files must be a positive integer",
        ),
    ],
)
def test_build_review_map_public_error_contract_is_structured(
    arguments: dict[str, Any], reason: str
) -> None:
    server = FastMCP("discover-review-map-error-test")
    register_change_tools(server, _ReviewMapService())
    tool = next(item for item in _local_tools(server) if item.name == "build_review_map")

    with pytest.raises(ToolError) as raised:
        asyncio.run(tool.run(arguments))

    payload = json.loads(str(raised.value))
    assert payload == {
        "code": "DISCOVER_REVIEW_MAP_REQUEST_INVALID",
        "message": "The build_review_map request is invalid.",
        "reason": reason,
        "field": "request",
        "corrective_actions": [
            "Use the exact current source fingerprint when supplied.",
            "Use a supported change source and positive bounded limits.",
        ],
        "retryable": False,
    }


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
