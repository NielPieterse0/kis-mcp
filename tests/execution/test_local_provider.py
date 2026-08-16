from __future__ import annotations

import asyncio
from typing import Any

from kis_mcp.execution.contracts import ExecutionProfile, ExecutionRequest, ExecutionSource
from kis_mcp.execution.local import LocalProcessExecutionProvider
from kis_mcp.execution.settings import load_execution_runner_settings


class _Runner:
    def __init__(self, results: list[Any]) -> None:
        self.results = list(results)
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def __call__(self, tool: str, arguments: dict[str, Any]) -> Any:
        self.calls.append((tool, arguments))
        return self.results.pop(0)


def _provider(runner: _Runner) -> LocalProcessExecutionProvider:
    settings = load_execution_runner_settings()
    return LocalProcessExecutionProvider(runner, settings.profile(settings.default_profile))


def _request() -> ExecutionRequest:
    return ExecutionRequest(
        request_id="local-1",
        project_id="kis-mcp",
        verification_profile_id="python",
        source=ExecutionSource(
            project_path=r"C:\Projects\fixture",
            revision="working-tree",
            exact=False,
        ),
        profile=ExecutionProfile(
            profile_id="local-process",
            backend_id="local-process",
            image_id="host-current",
            toolchain_id="repository-declared",
        ),
        executable="python",
        arguments=("-m", "pytest", "-q"),
        timeout_ms=30_000,
        evidence_limit_chars=20_000,
    )


def test_local_provider_preserves_existing_process_contract() -> None:
    runner = _Runner([{"text": "tests ok\n__KIS_EXECUTION_EXIT_CODE=0\n"}])
    result = asyncio.run(_provider(runner).execute(_request()))

    assert result.status == "passed"
    assert result.exit_code == 0
    assert result.evidence.stdout == "tests ok"
    assert result.cleanup.value == "not-required"
    tool, arguments = runner.calls[0]
    assert tool == "start_process"
    assert arguments["shell"] == "powershell.exe"
    assert "Set-Location -LiteralPath 'C:\\Projects\\fixture'" in arguments["command"]
    assert "__KIS_VERIFICATION_EXIT_CODE" in arguments["command"]


def test_local_provider_polls_process_until_terminal_receipt() -> None:
    runner = _Runner(
        [
            {"text": "Process started with PID 1234", "pid": 1234},
            {"text": "done\n__KIS_EXECUTION_EXIT_CODE=0\n"},
        ]
    )
    result = asyncio.run(_provider(runner).execute(_request()))

    assert result.status == "passed"
    assert [tool for tool, _ in runner.calls] == ["start_process", "read_process_output"]
    assert runner.calls[1][1]["pid"] == 1234


def test_local_provider_never_infers_success_without_terminal_receipt() -> None:
    runner = _Runner([{"text": "process state unknown"}])
    result = asyncio.run(_provider(runner).execute(_request()))

    assert result.status == "incomplete"
    assert result.exit_code is None
    assert result.failure_classification == "timeout_or_incomplete"


def test_local_provider_bounds_execution_evidence() -> None:
    request = _request()
    bounded = ExecutionRequest(
        request_id=request.request_id,
        project_id=request.project_id,
        verification_profile_id=request.verification_profile_id,
        source=request.source,
        profile=request.profile,
        executable=request.executable,
        arguments=request.arguments,
        timeout_ms=request.timeout_ms,
        evidence_limit_chars=24,
    )
    runner = _Runner(
        [{"text": f"{'x' * 100}\n__KIS_VERIFICATION_EXIT_CODE=0\n"}]
    )
    result = asyncio.run(_provider(runner).execute(bounded))

    assert result.status == "passed"
    assert result.evidence.truncated is True
    assert "execution evidence truncated" in result.evidence.stdout
    assert "__KIS_VERIFICATION_EXIT_CODE" not in result.evidence.stdout
