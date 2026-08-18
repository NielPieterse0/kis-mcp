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
                "status": "completed",
                "backend": arguments.get("backend") or "nvidia-nim",
                "review_type": arguments["review_type"],
                "source_fingerprint": "f" * 64,
                "evidence_complete": True,
                "summary": "review complete",
                "findings": [],
                "unknowns": [],
                "diagnostics": [],
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
    assert invoker.calls[3][1]["source"] == "working_tree"
    assert invoker.calls[3][1]["commit_ref"] is None
    assert invoker.calls[3][1]["base_ref"] is None
    assert invoker.calls[3][1]["head_ref"] is None


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
    ("complexity", "expected_max", "expected_reviews"),
    [
        ("small", 6, []),
        ("medium", 20, ["code-quality"]),
        ("large", 20, ["code-quality"]),
    ],
)
def test_execution_complexity_sets_base_workflow(
    complexity: str,
    expected_max: int,
    expected_reviews: list[str],
) -> None:
    invoker = _Invoker()
    result = asyncio.run(
        ChangeExecutionService(invoker).execute(
            project=r"C:\Projects\fixture",
            complexity=complexity,
        )
    )

    assert result.complexity == complexity
    assert result.risk_triggers == ()
    assert invoker.calls[0][1]["max_verifications"] == expected_max
    assert [arguments["review_type"] for name, arguments in invoker.calls if name == "review_change_with_agent"] == expected_reviews


def test_execution_risk_triggers_add_targeted_reviews_and_selection_terms() -> None:
    invoker = _Invoker()
    result = asyncio.run(
        ChangeExecutionService(invoker).execute(
            project=r"C:\Projects\fixture",
            complexity="small",
            task_terms=("tests",),
            risk_triggers=("architecture_boundary", "public_contract", "security"),
        )
    )

    assert result.complexity == "small"
    assert result.risk_triggers == ("architecture_boundary", "public_contract", "security")
    assert invoker.calls[0][1]["task_terms"] == ["tests", "architecture_boundary", "public_contract", "security"]
    assert [arguments["review_type"] for name, arguments in invoker.calls if name == "review_change_with_agent"] == ["architecture", "api-contracts", "safety-security"]


def test_execution_explicit_empty_reviews_do_not_disable_medium_base_review() -> None:
    invoker = _Invoker()
    result = asyncio.run(
        ChangeExecutionService(invoker).execute(
            project=r"C:\Projects\fixture",
            complexity="medium",
            review_types=(),
        )
    )

    assert result.status == "passed"
    assert [arguments["review_type"] for name, arguments in invoker.calls if name == "review_change_with_agent"] == ["code-quality"]


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


def test_execution_rejects_unknown_complexity_before_any_nested_call() -> None:
    invoker = _Invoker()
    with pytest.raises(ValueError, match="complexity"):
        asyncio.run(
            ChangeExecutionService(invoker).execute(
                project=r"C:\Projects\fixture",
                complexity="heroic",
            )
        )
    assert invoker.calls == []


def test_execution_rejects_unknown_risk_trigger_before_any_nested_call() -> None:
    invoker = _Invoker()
    with pytest.raises(ValueError, match="risk_triggers"):
        asyncio.run(
            ChangeExecutionService(invoker).execute(
                project=r"C:\Projects\fixture",
                risk_triggers=("made-up-risk",),
            )
        )
    assert invoker.calls == []


class _ReviewPayloadInvoker(_Invoker):
    def __init__(self, payload: dict[str, Any]) -> None:
        super().__init__()
        self.payload = payload

    async def __call__(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool_name == "review_change_with_agent":
            self.calls.append((tool_name, arguments))
            return dict(self.payload)
        return await super().__call__(tool_name, arguments)


@pytest.mark.parametrize(
    ("agent_status", "diagnostic"),
    [
        ("failed", "AGENT_BACKENDS_FAILED"),
        ("unavailable", "AGENT_BACKEND_UNAVAILABLE"),
        ("completed_unstructured", "AGENT_OUTPUT_NOT_STRUCTURED"),
    ],
)
def test_execution_never_counts_noncompleted_agent_outcome_as_review_success(
    agent_status: str,
    diagnostic: str,
) -> None:
    payload = {
        "schema_version": 1,
        "status": agent_status,
        "backend": "nvidia-nim",
        "review_type": "code-quality",
        "summary": "review did not complete successfully",
        "findings": [],
        "unknowns": [],
        "diagnostics": [diagnostic],
        "manual_fallback": {
            "required": True,
            "mode": "exact-diff",
            "review_type": "code-quality",
            "reason": "all_configured_backends_failed_or_unavailable",
        },
    }
    result = asyncio.run(
        ChangeExecutionService(_ReviewPayloadInvoker(payload)).execute(
            project=r"C:\Projects\fixture",
            complexity="medium",
        )
    )

    assert result.status == "incomplete"
    assert result.review_error_count == 1
    assert result.reviews[0].status == "error"
    assert result.reviews[0].error_code == diagnostic
    assert result.reviews[0].payload == payload


def test_execution_rejects_completed_review_with_mismatched_source_fingerprint() -> None:
    payload = {
        "schema_version": 1,
        "status": "completed",
        "backend": "codex-cli",
        "review_type": "code-quality",
        "source_fingerprint": "a" * 64,
        "evidence_complete": True,
        "summary": "review complete",
        "findings": [],
        "unknowns": [],
        "diagnostics": [],
    }

    result = asyncio.run(
        ChangeExecutionService(_ReviewPayloadInvoker(payload)).execute(
            project=r"C:\Projects\fixture",
            complexity="medium",
        )
    )

    assert result.status == "incomplete"
    assert result.review_error_count == 1
    assert result.reviews[0].error_code == "AGENT_REVIEW_SOURCE_MISMATCH"


def test_execution_rejects_completed_review_without_complete_evidence() -> None:
    payload = {
        "schema_version": 1,
        "status": "completed",
        "backend": "codex-cli",
        "review_type": "code-quality",
        "source_fingerprint": "f" * 64,
        "evidence_complete": False,
        "summary": "review complete",
        "findings": [],
        "unknowns": [],
        "diagnostics": [],
    }

    result = asyncio.run(
        ChangeExecutionService(_ReviewPayloadInvoker(payload)).execute(
            project=r"C:\Projects\fixture",
            complexity="medium",
        )
    )

    assert result.status == "incomplete"
    assert result.reviews[0].error_code == "AGENT_REVIEW_EVIDENCE_INCOMPLETE"


def test_execution_passes_exact_commit_selector_to_specialist_review() -> None:
    invoker = _Invoker()
    asyncio.run(
        ChangeExecutionService(invoker).execute(
            project=r"C:\Projects\fixture",
            source="commit",
            commit_ref="abc123",
            complexity="medium",
        )
    )

    review_call = next(arguments for name, arguments in invoker.calls if name == "review_change_with_agent")
    assert review_call["source"] == "commit"
    assert review_call["commit_ref"] == "abc123"
    assert review_call["base_ref"] is None
    assert review_call["head_ref"] is None


class _SlowReviewInvoker(_Invoker):
    async def __call__(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool_name == "review_change_with_agent":
            self.calls.append((tool_name, arguments))
            await asyncio.sleep(0.05)
            return {
                "status": "completed",
                "source_fingerprint": "f" * 64,
                "evidence_complete": True,
                "summary": "late review",
                "findings": [],
                "unknowns": [],
                "diagnostics": [],
            }
        return await super().__call__(tool_name, arguments)


def test_execution_bounds_aggregate_specialist_review_phase() -> None:
    invoker = _SlowReviewInvoker()
    result = asyncio.run(
        ChangeExecutionService(invoker).execute(
            project=r"C:\Projects\fixture",
            complexity="small",
            review_types=("code-quality", "safety-security"),
            review_timeout_ms=10,
        )
    )

    assert result.status == "incomplete"
    assert result.review_error_count == 2
    assert [item.error_code for item in result.reviews] == [
        "AGENT_REVIEW_PHASE_DEADLINE_EXCEEDED",
        "AGENT_REVIEW_PHASE_DEADLINE_EXCEEDED",
    ]
    assert len([name for name, _ in invoker.calls if name == "review_change_with_agent"]) == 1
