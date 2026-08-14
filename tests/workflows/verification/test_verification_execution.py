from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import pytest

from kis_mcp.workflows.verification.execution import (
    VerificationExecutionError,
    VerificationExecutionService,
)


@dataclass
class _Inspection:
    verification: dict[str, Any]


class _Inspector:
    def __init__(self, declarations: list[dict[str, Any]]) -> None:
        self.declarations = declarations
        self.calls: list[str] = []

    def inspect(self, request: Any) -> _Inspection:
        self.calls.append(request.path)
        return _Inspection(verification={"declarations": self.declarations})


class _Runner:
    def __init__(self, results: list[Any]) -> None:
        self.results = list(results)
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def __call__(self, tool: str, arguments: dict[str, Any]) -> Any:
        self.calls.append((tool, arguments))
        return self.results.pop(0)


def _declaration(
    *,
    verification_id: str = "python-pytest",
    profile: str = "python",
    arguments: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "id": verification_id,
        "title": "Run Python pytest suite",
        "category": "test",
        "source_path": "tests/test_sample.py",
        "profile": profile,
        "arguments": arguments or ["-m", "pytest", "-q"],
        "authority": "discovered_only",
        "execution_available": False,
    }


def test_unknown_verification_id_is_rejected_before_process_execution() -> None:
    runner = _Runner([])
    service = VerificationExecutionService(
        inspector=_Inspector([_declaration()]),
        runner=runner,
    )

    with pytest.raises(VerificationExecutionError, match="VERIFICATION_ID_UNKNOWN"):
        asyncio.run(
            service.run(
                project=r"C:\Projects\fixture",
                verification_id="missing",
                timeout_ms=30_000,
            )
        )

    assert runner.calls == []


def test_supported_profile_builds_fixed_process_command_and_passes() -> None:
    runner = _Runner([{"text": "tests ok\n__KIS_VERIFICATION_EXIT_CODE=0\n"}])
    service = VerificationExecutionService(
        inspector=_Inspector([_declaration()]),
        runner=runner,
    )
    result = asyncio.run(
        service.run(
            project=r"C:\Projects\fixture",
            verification_id="python-pytest",
            timeout_ms=30_000,
        )
    )

    assert result.status == "passed"
    assert result.exit_code == 0
    assert result.failure_classification == "none"
    assert result.command_identity
    assert result.evidence == "tests ok"
    assert runner.calls[0][0] == "start_process"
    arguments = runner.calls[0][1]
    assert set(arguments) == {"command", "timeout_ms", "shell"}
    assert arguments["timeout_ms"] == 30_000
    assert arguments["shell"] == "powershell.exe"
    assert "Set-Location -LiteralPath 'C:\\Projects\\fixture'" in arguments["command"]
    assert "$kisSource = Join-Path -Path 'C:\\Projects\\fixture' -ChildPath 'src'" in arguments["command"]
    assert "Test-Path -LiteralPath $kisSource -PathType Container" in arguments["command"]
    assert "$env:PYTHONPATH" in arguments["command"]
    assert "pytest" in arguments["command"]
    assert "__KIS_VERIFICATION_EXIT_CODE" in arguments["command"]


def test_nonzero_exit_is_classified_as_verification_failure() -> None:
    runner = _Runner([{"text": "failure output\n__KIS_VERIFICATION_EXIT_CODE=2\n"}])
    result = asyncio.run(
        VerificationExecutionService(
            inspector=_Inspector([_declaration()]),
            runner=runner,
        ).run(
            project=r"C:\Projects\fixture",
            verification_id="python-pytest",
            timeout_ms=30_000,
        )
    )

    assert result.status == "failed"
    assert result.exit_code == 2
    assert result.failure_classification == "verification_failed"
    assert result.evidence == "failure output"


def test_structured_process_pid_is_polled_and_can_complete() -> None:
    runner = _Runner(
        [
            {"text": "Process started with PID 1234", "pid": 1234},
            {"text": "done\n__KIS_VERIFICATION_EXIT_CODE=0\n"},
        ]
    )
    result = asyncio.run(
        VerificationExecutionService(
            inspector=_Inspector([_declaration()]),
            runner=runner,
        ).run(
            project=r"C:\Projects\fixture",
            verification_id="python-pytest",
            timeout_ms=30_000,
        )
    )

    assert result.status == "passed"
    assert runner.calls[1][0] == "read_process_output"
    assert runner.calls[1][1]["pid"] == 1234
    assert 1 <= runner.calls[1][1]["timeout_ms"] <= 30_000
    assert runner.calls[1][1]["offset"] == 0
    assert runner.calls[1][1]["length"] == 200


def test_intermediate_process_output_is_repolled_until_terminal_receipt() -> None:
    runner = _Runner(
        [
            {"text": "Process started with PID 1234 (shell: powershell.exe)\nInitial output:"},
            {"text": "tests still running"},
            {"text": "182 passed\n__KIS_VERIFICATION_EXIT_CODE=0\n"},
        ]
    )
    result = asyncio.run(
        VerificationExecutionService(
            inspector=_Inspector([_declaration()]),
            runner=runner,
        ).run(
            project=r"C:\Projects\fixture",
            verification_id="python-pytest",
            timeout_ms=30_000,
        )
    )

    assert result.status == "passed"
    assert result.exit_code == 0
    assert "tests still running" in result.evidence
    assert "182 passed" in result.evidence
    assert [tool for tool, _ in runner.calls] == [
        "start_process",
        "read_process_output",
        "read_process_output",
    ]
    assert all(
        1 <= arguments["timeout_ms"] <= 30_000
        for tool, arguments in runner.calls
        if tool == "read_process_output"
    )


def test_textual_process_pid_reconciles_nonzero_terminal_receipt() -> None:
    runner = _Runner(
        [
            {"text": "Process started with PID 4321 (shell: powershell.exe)"},
            {"text": "six failures\n__KIS_VERIFICATION_EXIT_CODE=1\n"},
        ]
    )
    result = asyncio.run(
        VerificationExecutionService(
            inspector=_Inspector([_declaration()]),
            runner=runner,
        ).run(
            project=r"C:\Projects\fixture",
            verification_id="python-pytest",
            timeout_ms=30_000,
        )
    )

    assert result.status == "failed"
    assert result.exit_code == 1
    assert result.failure_classification == "verification_failed"
    assert runner.calls[1][1]["pid"] == 4321


def test_textual_process_pid_polling_respects_original_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = iter((10.0, 10.01, 10.03, 10.03))
    monkeypatch.setattr(
        "kis_mcp.workflows.verification.execution.time.perf_counter",
        lambda: next(clock),
    )
    runner = _Runner(
        [
            {"text": "Process started with PID 9876"},
            {"text": "tests still running"},
        ]
    )
    result = asyncio.run(
        VerificationExecutionService(
            inspector=_Inspector([_declaration()]),
            runner=runner,
        ).run(
            project=r"C:\Projects\fixture",
            verification_id="python-pytest",
            timeout_ms=20,
        )
    )

    assert result.status == "incomplete"
    assert [tool for tool, _ in runner.calls] == ["start_process", "read_process_output"]
    assert 1 <= runner.calls[1][1]["timeout_ms"] < 20


def test_missing_exit_marker_is_incomplete_not_success() -> None:
    runner = _Runner([{"text": "process state unknown"}])
    result = asyncio.run(
        VerificationExecutionService(
            inspector=_Inspector([_declaration()]),
            runner=runner,
        ).run(
            project=r"C:\Projects\fixture",
            verification_id="python-pytest",
            timeout_ms=30_000,
        )
    )

    assert result.status == "incomplete"
    assert result.exit_code is None
    assert result.failure_classification == "timeout_or_incomplete"


def test_unsupported_profile_is_rejected_before_runner() -> None:
    runner = _Runner([])
    service = VerificationExecutionService(
        inspector=_Inspector([_declaration(profile="custom-shell")]),
        runner=runner,
    )

    with pytest.raises(VerificationExecutionError, match="VERIFICATION_PROFILE_UNSUPPORTED"):
        asyncio.run(
            service.run(
                project=r"C:\Projects\fixture",
                verification_id="python-pytest",
                timeout_ms=30_000,
            )
        )
    assert runner.calls == []
