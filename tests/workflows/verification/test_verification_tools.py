from __future__ import annotations

import asyncio
from typing import Any

import pytest
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from kis_mcp.workflows.verification.contracts import (
    VerificationResult,
    VerificationSelectionItem,
    VerificationSelectionResult,
)
from kis_mcp.workflows.verification.execution import VerificationExecutionError
from kis_mcp.workflows.verification.tools import (
    register_verification_selection_tool,
    register_verification_tool,
)


class _Service:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[dict[str, Any]] = []

    async def run(self, **kwargs: Any) -> VerificationResult:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return VerificationResult(
            verification_id=kwargs["verification_id"],
            title="Pytest",
            category="test",
            source_path="tests/test_sample.py",
            profile="python",
            arguments=("-m", "pytest", "-q"),
            command_identity="a" * 64,
            status="passed",
            exit_code=0,
            duration_ms=1,
            evidence="ok",
            failure_classification="none",
            truncated=False,
        )


def test_run_verification_tool_has_narrow_process_surface() -> None:
    server = FastMCP("verification-tool-test")
    service = _Service()
    register_verification_tool(server, service)

    tool = {item.name: item for item in asyncio.run(server.list_tools())}["run_verification"]
    properties = tool.to_mcp_tool().input_schema["properties"]
    assert set(properties) == {
        "project",
        "verification_id",
        "timeout_ms",
        "stall_timeout_ms",
    }
    assert "command" not in properties
    assert tool.annotations.read_only_hint is False
    result = asyncio.run(
        server.call_tool(
            "run_verification",
            {
                "project": r"C:\Projects\fixture",
                "verification_id": "python-pytest",
                "timeout_ms": 45_000,
                "stall_timeout_ms": 15_000,
            },
        )
    )

    assert result.structured_content["contract"] == "verification-result-v1"
    assert result.structured_content["status"] == "passed"
    assert service.calls[0]["project"] == r"C:\Projects\fixture"
    assert service.calls[0]["verification_id"] == "python-pytest"
    assert service.calls[0]["timeout_ms"] == 45_000
    assert service.calls[0]["stall_timeout_ms"] == 15_000
    assert callable(service.calls[0]["progress_reporter"])


def test_structural_verification_errors_are_not_hr_policy_codes() -> None:
    server = FastMCP("verification-error-test")
    register_verification_tool(
        server,
        _Service(
            error=VerificationExecutionError(
                "VERIFICATION_ID_UNKNOWN",
                "No such declaration.",
            )
        ),
    )
    with pytest.raises(ToolError) as raised:
        asyncio.run(
            server.call_tool(
                "run_verification",
                {
                    "project": r"C:\Projects\fixture",
                    "verification_id": "missing",
                    "timeout_ms": 30_000,
                },
            )
        )
    assert "VERIFICATION_ID_UNKNOWN" in str(raised.value)
    assert "HR-" not in str(raised.value)


class _SelectionService:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def select(self, **kwargs: Any) -> VerificationSelectionResult:
        self.calls.append(kwargs)
        return VerificationSelectionResult(
            project=kwargs["project"],
            source_fingerprint="f" * 64,
            selected=(
                VerificationSelectionItem(
                    verification_id="python-pytest",
                    category="test",
                    reason="Affected tests",
                    profile="python",
                    source_path="pyproject.toml",
                ),
            ),
            skipped=(),
            omitted_count=0,
            truncated=False,
        )


def test_select_change_verification_is_read_only_and_does_not_accept_commands() -> None:
    server = FastMCP("verification-selection-test")
    service = _SelectionService()
    register_verification_selection_tool(server, service)
    tool = {item.name: item for item in asyncio.run(server.list_tools())}[
        "select_change_verification"
    ]
    assert tool.annotations.read_only_hint is True
    assert "command" not in tool.to_mcp_tool().input_schema["properties"]

    result = asyncio.run(
        tool.run(
            {
                "project": r"C:\Projects\fixture",
                "task_terms": ["tests"],
                "max_verifications": 3,
            }
        )
    )

    assert result.structured_content["contract"] == "verification-selection-v1"
    assert result.structured_content["selected"][0]["execution_available"] is False
    assert service.calls[0]["task_terms"] == ("tests",)
