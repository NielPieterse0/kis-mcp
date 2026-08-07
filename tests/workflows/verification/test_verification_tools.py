from __future__ import annotations

import asyncio
from typing import Any

import pytest
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from kis_mcp.workflows.verification.contracts import VerificationResult
from kis_mcp.workflows.verification.execution import VerificationExecutionError
from kis_mcp.workflows.verification.tools import register_verification_tool


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
    properties = tool.parameters["properties"]
    assert set(properties) == {"project", "verification_id", "timeout_ms"}
    assert "command" not in properties
    assert tool.annotations.readOnlyHint is False
    result = asyncio.run(
        tool.run(
            {
                "project": r"C:\Projects\fixture",
                "verification_id": "python-pytest",
                "timeout_ms": 45_000,
            }
        )
    )

    assert result.structured_content["contract"] == "verification-result-v1"
    assert result.structured_content["status"] == "passed"
    assert service.calls == [
        {
            "project": r"C:\Projects\fixture",
            "verification_id": "python-pytest",
            "timeout_ms": 45_000,
        }
    ]


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
    tool = {item.name: item for item in asyncio.run(server.list_tools())}["run_verification"]

    with pytest.raises(ToolError) as raised:
        asyncio.run(
            tool.run(
                {
                    "project": r"C:\Projects\fixture",
                    "verification_id": "missing",
                    "timeout_ms": 30_000,
                }
            )
        )
    assert "VERIFICATION_ID_UNKNOWN" in str(raised.value)
    assert "HR-" not in str(raised.value)
