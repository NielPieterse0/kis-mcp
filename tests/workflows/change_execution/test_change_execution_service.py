from __future__ import annotations

import asyncio
from typing import Any

import pytest

from kis_mcp.workflows.change_execution.service import (
    ChangeExecutionInvocationError,
    ChangeExecutionService,
)


class _Invoker:
    def __init__(self, *, failed_verification: bool = False, review_error: bool = False) -> None:
        self.failed_verification = failed_verification
        self.review_error = review_error
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def __call__(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((tool_name, arguments))
        if tool_name == "select_change_verification":
            return {
                "contract": "verification-selection-v1",
                "source_fingerprint": "f" * 64,
                "selected": [
                    {"verification_id": "repo-verify"},
                    {"verification_id": "python-pytest"},
                ],
                "skipped": [],
                "omitted_count": 0,
                "truncated": False,
            }
        if tool_name == "run_verification":
            failed = self.failed_verification and arguments["verification_id"] == "python-pytest"
            return {
                "contract": "verification-result-v1",
                "verification_id": arguments["verification_id"],
                "status": "failed" if failed else "passed",
                "failure_classification": "verification_failed" if failed else "none",
            }
        if tool_name == "review_change_with_agent":
            if self.review_error and arguments["review_type"] == "safety-security":
                raise ChangeExecutionInvocationError("AGENT_REVIEW_FAILED", "backend unavailable")
            return {
                "backend": arguments.get("backend") or "nvidia-nim",
                "review_type": arguments["review_type"],
                "findings": [],
            }
        raise AssertionError(f"unexpected nested tool {tool_name}")


def test_execution_uses_only_selected_verifications_and_allowlisted_reviews() -> None:
    invoker = _Invoker()
    result = asyncio.run(
        ChangeExecutionService(invoker).execute(
            project=r"C:\Projects\fixture",
            task_terms=("tests",),
            max_verifications=2,
            verification_timeout_ms=45_000,
            review_types=("code-quality", "safety-security"),
            review_backend="codex-cli",
        )
    )

    assert result.status == "passed"
    assert result.source_fingerprint == "f" * 64
    assert [item.step_id for item in result.verifications] == ["repo-verify", "python-pytest"]
    assert [item.step_id for item in result.reviews] == ["code-quality", "safety-security"]
    assert [name for name, _ in invoker.calls] == [
        "select_change_verification",
        "run_verification",
        "run_verification",
        "review_change_with_agent",
        "review_change_with_agent",
    ]
    assert all("command" not in arguments for _, arguments in invoker.calls)
    assert invoker.calls[0][1]["project"] == r"C:\Projects\fixture"
    assert invoker.calls[1][1]["project"] == r"C:\Projects\fixture"
    assert invoker.calls[3][1]["path"] == r"C:\Projects\fixture"
    assert invoker.calls[1][1]["verification_id"] == "repo-verify"
    assert invoker.calls[2][1]["verification_id"] == "python-pytest"
    assert invoker.calls[3][1]["backend"] == "codex-cli"


def test_execution_retains_verification_failure_and_review_error() -> None:
    result = asyncio.run(
        ChangeExecutionService(
            _Invoker(failed_verification=True, review_error=True)
        ).execute(
            project=r"C:\Projects\fixture",
            review_types=("code-quality", "safety-security"),
        )
    )

    assert result.status == "failed"
    assert result.verification_failed_count == 1
    assert result.review_error_count == 1
    assert result.verifications[1].status == "failed"
    assert result.reviews[1].status == "error"
    assert result.reviews[1].error_code == "AGENT_REVIEW_FAILED"


@pytest.mark.parametrize(
    ("risk_profile", "expected_max", "expected_reviews"),
    [
        ("lean", 6, []),
        ("standard", 20, ["code-quality"]),
        ("rigorous", 20, ["code-quality", "safety-security", "architecture"]),
    ],
)
def test_execution_risk_profile_sets_default_weight(
    risk_profile: str,
    expected_max: int,
    expected_reviews: list[str],
) -> None:
    invoker = _Invoker()
    result = asyncio.run(
        ChangeExecutionService(invoker).execute(
            project=r"C:\Projects\fixture",
            risk_profile=risk_profile,
        )
    )

    assert result.risk_profile == risk_profile
    assert invoker.calls[0][1]["max_verifications"] == expected_max
    assert [
        arguments["review_type"]
        for name, arguments in invoker.calls
        if name == "review_change_with_agent"
    ] == expected_reviews


def test_execution_explicit_empty_reviews_disable_risk_default_reviews() -> None:
    invoker = _Invoker()
    result = asyncio.run(
        ChangeExecutionService(invoker).execute(
            project=r"C:\Projects\fixture",
            risk_profile="standard",
            review_types=(),
        )
    )

    assert result.status == "passed"
    assert all(name != "review_change_with_agent" for name, _ in invoker.calls)


def test_execution_rejects_unknown_review_type_before_any_nested_call() -> None:
    invoker = _Invoker()
    with pytest.raises(ValueError, match="review_type"):
        asyncio.run(
            ChangeExecutionService(invoker).execute(
                project=r"C:\Projects\fixture",
                review_types=("made-up-review",),
            )
        )
    assert invoker.calls == []


def test_execution_rejects_unknown_risk_profile_before_any_nested_call() -> None:
    invoker = _Invoker()
    with pytest.raises(ValueError, match="risk_profile"):
        asyncio.run(
            ChangeExecutionService(invoker).execute(
                project=r"C:\Projects\fixture",
                risk_profile="heroic",
            )
        )
    assert invoker.calls == []
