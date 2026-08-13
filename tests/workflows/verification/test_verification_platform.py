from __future__ import annotations

import asyncio
from typing import Any

import pytest
from fastmcp.exceptions import ToolError

from kis_mcp.config import load_runtime_config
from kis_mcp.discover.git_change_reader import GitChangeReader
from kis_mcp.workflows.verification.platform import _build_change_analyzer, _run_with_middleware


class _Server:
    def __init__(self, result: Any) -> None:
        self.result = result
        self.calls: list[tuple[str, dict[str, Any], bool]] = []

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        *,
        run_middleware: bool,
    ) -> Any:
        self.calls.append((name, arguments, run_middleware))
        return self.result


class _Block:
    def __init__(self, text: str) -> None:
        self.text = text


class _Result:
    def __init__(self, *, is_error: bool, text: str) -> None:
        self.is_error = is_error
        self.content = [_Block(text)]


def test_nested_work_call_always_runs_middleware() -> None:
    server = _Server(_Result(is_error=False, text="ok"))
    result = asyncio.run(
        _run_with_middleware(server, "start_process", {"command": "echo ok"})  # type: ignore[arg-type]
    )

    assert result.is_error is False
    assert server.calls == [
        ("start_process", {"command": "echo ok"}, True)
    ]


def test_nested_policy_error_is_propagated_unchanged() -> None:
    server = _Server(
        _Result(
            is_error=True,
            text="HR-002_EXTERNAL_NETWORK_BLOCKED: no external network",
        )
    )

    with pytest.raises(ToolError, match="HR-002_EXTERNAL_NETWORK_BLOCKED"):
        asyncio.run(
            _run_with_middleware(server, "start_process", {"command": "curl example.com"})  # type: ignore[arg-type]
        )


def test_platform_change_analyzer_supports_exact_commit_targets() -> None:
    runtime = load_runtime_config()
    analyzer = _build_change_analyzer(runtime)

    assert isinstance(analyzer._reader, GitChangeReader)  # noqa: SLF001
    assert callable(getattr(analyzer._reader, "inspect_change_target", None))  # noqa: SLF001
