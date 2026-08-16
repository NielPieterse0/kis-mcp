from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from kis_mcp.workflows.completion.contracts import CompletionResult
from kis_mcp.workflows.completion.service import CompletionInvocationError
from kis_mcp.workflows.completion.tools import register_completion_tool


class Service:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def prepare(self, **kwargs: Any) -> CompletionResult:
        self.calls.append(kwargs)
        return CompletionResult(
            project_id=kwargs["project_id"],
            source_commit_sha=kwargs["commit"],
            published_head_sha="d" * 40,
            branch=kwargs["branch"],
            execution={"contract": "change-execution-result-v2", "status": "passed"},
            publication={"state": "published", "source_commit_sha": kwargs["commit"], "commit_sha": "d" * 40},
            pull_request={"state": "open", "pull_number": 9, "head_sha": "d" * 40},
            operation_id="prp-" + "f" * 64,
            operation_state="applied",
            elapsed_ms=3,
            stage_timings_ms={"verification": 1, "publication": 1, "pull_request": 1},
        )


def test_prepare_reviewable_pull_request_has_bounded_surface() -> None:
    server = FastMCP("completion-test")
    service = Service()
    register_completion_tool(server, service)
    tool = {item.name: item for item in asyncio.run(server.list_tools())}[
        "prepare_reviewable_pull_request"
    ]
    properties = tool.parameters["properties"]
    assert set(properties) == {
        "project_id",
        "commit",
        "source_base",
        "branch",
        "expected_remote_branch",
        "expected_remote_default",
        "title",
        "body",
        "approved",
        "task_terms",
        "complexity",
        "risk_triggers",
        "max_verifications",
        "verification_timeout_ms",
        "review_types",
        "review_backend",
        "review_model",
        "documentation_impact",
        "residual_state",
        "deadline_ms",
        "reconcile_only",
    }
    for forbidden in (
        "command", "tool_name", "operation", "repository", "remote_url",
        "merge", "delete", "cleanup", "force", "policy",
    ):
        assert forbidden not in properties
    result = asyncio.run(tool.run({
        "project_id": "college",
        "commit": "a" * 40,
        "source_base": "e" * 40,
        "branch": "feature/example",
        "expected_remote_branch": None,
        "expected_remote_default": "b" * 40,
        "title": "Review exact change",
        "body": "Ready for review.",
        "approved": True,
    }))

    assert result.structured_content["contract"] == "completion-result-v1"
    assert result.structured_content["status"] == "reviewable"
    assert service.calls[0]["review_types"] is None
    assert service.calls[0]["complexity"] == "medium"
    assert service.calls[0]["risk_triggers"] == ()
    assert tool.annotations.readOnlyHint is False
    assert tool.annotations.destructiveHint is False
    assert tool.annotations.idempotentHint is True


class FailingService(Service):
    async def prepare(self, **kwargs: Any) -> CompletionResult:
        raise CompletionInvocationError(
            "COMPLETION_PULL_REQUEST_FAILED",
            "TimeoutError: response lost",
            retryable=True,
            stage="pull_request",
            completed_steps=("verification", "publication"),
        )


def test_prepare_reviewable_pull_request_serializes_partial_success_diagnostics() -> None:
    server = FastMCP("completion-error-test")
    register_completion_tool(server, FailingService())
    tool = {item.name: item for item in asyncio.run(server.list_tools())}[
        "prepare_reviewable_pull_request"
    ]
    request = {
        "project_id": "college",
        "commit": "a" * 40,
        "source_base": "e" * 40,
        "branch": "feature/example",
        "expected_remote_branch": None,
        "expected_remote_default": "b" * 40,
        "title": "Review exact change",
        "body": "Ready for review.",
        "approved": True,
    }

    with pytest.raises(ToolError) as raised:
        asyncio.run(tool.run(request))

    payload = json.loads(str(raised.value))
    assert payload == {
        "code": "COMPLETION_PULL_REQUEST_FAILED",
        "completed_steps": ["verification", "publication"],
        "message": "Completion coordination failed.",
        "reason": "TimeoutError: response lost",
        "retryable": True,
        "stage": "pull_request",
    }
