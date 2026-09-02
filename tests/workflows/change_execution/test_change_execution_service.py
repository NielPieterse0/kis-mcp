from __future__ import annotations

import asyncio
import json
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


class _CanonicalVerificationInvoker(_Invoker):
    async def __call__(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool_name == "select_change_verification":
            self.calls.append((tool_name, arguments))
            return {
                "contract": "verification-selection-v1",
                "source_fingerprint": "f" * 64,
                "selected": [
                    {
                        "verification_id": "powershell-verify-script",
                        "category": "repository_verification",
                        "profile": "powershell_verify",
                    },
                    {
                        "verification_id": "python-module-verify",
                        "category": "repository_verification",
                        "profile": "python",
                    },
                    {
                        "verification_id": "python-pytest",
                        "category": "test",
                        "profile": "python",
                    },
                ],
                "skipped": [],
                "omitted_count": 0,
                "truncated": False,
            }
        return await super().__call__(tool_name, arguments)


def test_passed_canonical_repository_verifier_suppresses_redundant_verifications() -> None:
    invoker = _CanonicalVerificationInvoker()
    result = asyncio.run(
        ChangeExecutionService(invoker).execute(
            project=r"C:\Projects\fixture",
            review_types=(),
        )
    )

    assert result.status == "passed"
    assert [name for name, _ in invoker.calls].count("run_verification") == 1
    assert [name for name, _ in invoker.calls][:2] == [
        "select_change_verification",
        "run_verification",
    ]
    assert [item.status for item in result.verifications] == [
        "passed",
        "completed",
        "completed",
    ]
    for item in result.verifications[1:]:
        assert item.payload == {
            "disposition": "redundant",
            "reason": "CANONICAL_REPOSITORY_VERIFICATION_PASSED",
            "canonical_verification_id": "powershell-verify-script",
        }


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


class _TransientReviewTransportInvoker(_Invoker):
    def __init__(self, *, persistent: bool = False) -> None:
        super().__init__()
        self.persistent = persistent
        self.review_attempts = 0

    async def __call__(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool_name == "review_change_with_agent":
            self.calls.append((tool_name, arguments))
            self.review_attempts += 1
            if self.persistent or self.review_attempts == 1:
                raise RuntimeError("simulated connector 502")
            return {
                "status": "completed",
                "backend": "nvidia-nim",
                "review_type": arguments["review_type"],
                "source_fingerprint": "f" * 64,
                "evidence_complete": True,
                "summary": "review complete after retry",
                "findings": [],
                "unknowns": [],
                "diagnostics": [],
            }
        return await super().__call__(tool_name, arguments)


def test_execution_retries_untyped_review_transport_failure_once() -> None:
    invoker = _TransientReviewTransportInvoker()
    result = asyncio.run(
        ChangeExecutionService(invoker).execute(
            project=r"C:\Projects\fixture",
            complexity="medium",
        )
    )

    assert result.status == "passed"
    assert result.review_error_count == 0
    assert invoker.review_attempts == 2


def test_execution_converts_persistent_untyped_review_failure_to_incomplete() -> None:
    invoker = _TransientReviewTransportInvoker(persistent=True)
    result = asyncio.run(
        ChangeExecutionService(invoker).execute(
            project=r"C:\Projects\fixture",
            complexity="medium",
        )
    )

    assert result.status == "incomplete"
    assert result.review_error_count == 1
    assert invoker.review_attempts == 2
    assert result.reviews[0].error_code == "CHANGE_EXECUTION_NESTED_INVOCATION_FAILED"
    assert result.reviews[0].reason == "review_change_with_agent failed with RuntimeError"


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


class _EnsembleInvoker(_Invoker):
    async def __call__(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool_name == "review_change_with_agent":
            self.calls.append((tool_name, arguments))
            return {
                "status": "completed",
                "backend": arguments.get("backend") or "nvidia-nim",
                "review_type": arguments["review_type"],
                "source_fingerprint": "f" * 64,
                "evidence_complete": True,
                "summary": "ensemble review complete",
                "findings": [{
                    "severity": "medium",
                    "path": "src/example.py",
                    "line": 10,
                    "claim": "shared candidate",
                    "evidence": "bounded evidence",
                    "recommendation": "fix it",
                    "confidence": "high",
                }],
                "unknowns": [],
                "diagnostics": [],
                **(
                    {
                        "model_profile": arguments["model"],
                        "model": {
                            "nano": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
                            "super": "nvidia/nemotron-3-super-120b-a12b",
                            "ultra": "nvidia/nemotron-3-ultra-550b-a55b",
                        }[arguments["model"]],
                    }
                    if "model" in arguments
                    else {}
                ),
            }
        return await super().__call__(tool_name, arguments)

def test_execution_runs_bounded_independent_reviewer_ensemble() -> None:
    invoker = _EnsembleInvoker()
    result = asyncio.run(ChangeExecutionService(invoker).execute(
        project=r"C:\Projects\fixture",
        complexity="small",
        review_types=("code-quality",),
        reviewers=(
            {"reviewer_id": "fast", "backend": "nvidia-nim", "model": "nano"},
            {"reviewer_id": "deep", "backend": "codex-cli"},
        ),
    ))

    review_calls = [args for name, args in invoker.calls if name == "review_change_with_agent"]
    assert len(review_calls) == 2
    assert [call.get("backend") for call in review_calls] == ["nvidia-nim", "codex-cli"]
    assert all("reviewer_id=" in call["instructions"] for call in review_calls)
    assert all(call["source"] == "working_tree" for call in review_calls)
    assert result.status == "passed"
    assert result.review_ensemble is not None
    assert result.review_ensemble["reviewer_count"] == 2
    assert result.review_ensemble["invocation_count"] == 2
    assert result.review_ensemble["unique_finding_count"] == 1
    assert result.reviews[0].payload is not None
    assert result.reviews[0].payload["ensemble_provenance"] == {
        "reviewer_id": "fast", "backend": "nvidia-nim", "requested_model_profile": "nano",
        "round": 1, "review_type": "code-quality", "source": "working_tree",
        "commit_ref": None, "base_ref": None, "head_ref": None, "source_fingerprint": "f" * 64,
    }
    assert result.review_ensemble["duplicate_finding_count"] == 1
    assert result.review_ensemble["gate_authority"] == {
        "verification": False, "merge_readiness": False, "mutation": False
    }


def test_execution_rejects_unbounded_or_ambiguous_ensemble_requests() -> None:
    invoker = _Invoker()
    with pytest.raises(ValueError, match="at most four"):
        asyncio.run(ChangeExecutionService(invoker).execute(
            project=r"C:\Projects\fixture",
            reviewers=tuple(
                {"reviewer_id": f"r{index}", "backend": "codex-cli"}
                for index in range(5)
            ),
        ))
    with pytest.raises(ValueError, match="review_rounds"):
        asyncio.run(ChangeExecutionService(invoker).execute(
            project=r"C:\Projects\fixture",
            reviewers=({"reviewer_id": "one", "backend": "codex-cli"},),
            review_rounds=3,
        ))
    with pytest.raises(ValueError, match="legacy review_backend"):
        asyncio.run(ChangeExecutionService(invoker).execute(
            project=r"C:\Projects\fixture",
            reviewers=({"reviewer_id": "one", "backend": "codex-cli"},),
            review_backend="codex-cli",
        ))
    assert invoker.calls == []


class _DissentEnsembleInvoker(_Invoker):
    async def __call__(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool_name == "review_change_with_agent":
            self.calls.append((tool_name, arguments))
            reviewer_id = arguments["instructions"].split("reviewer_id=", 1)[1].split(";", 1)[0]
            severity = "high" if reviewer_id == "deep" else "medium"
            return {
                "status": "completed",
                "backend": arguments["backend"],
                "review_type": arguments["review_type"],
                "source_fingerprint": "f" * 64,
                "evidence_complete": True,
                "summary": "review complete",
                "findings": [{
                    "severity": severity,
                    "path": "src/example.py",
                    "line": 11,
                    "claim": "same claim",
                    "evidence": "same evidence",
                    "recommendation": "inspect it",
                    "confidence": "high",
                }],
                "unknowns": [],
                "diagnostics": [],
                "cost": 0.25,
                **(
                    {
                        "model_profile": arguments["model"],
                        "model": {
                            "nano": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
                            "super": "nvidia/nemotron-3-super-120b-a12b",
                            "ultra": "nvidia/nemotron-3-ultra-550b-a55b",
                        }[arguments["model"]],
                    }
                    if "model" in arguments
                    else {}
                ),
            }
        return await super().__call__(tool_name, arguments)

def test_execution_retains_ensemble_dissent_and_cost_telemetry() -> None:
    result = asyncio.run(ChangeExecutionService(_DissentEnsembleInvoker()).execute(
        project=r"C:\Projects\fixture",
        complexity="small",
        review_types=("code-quality",),
        reviewers=(
            {"reviewer_id": "fast", "backend": "nvidia-nim", "model": "nano"},
            {"reviewer_id": "deep", "backend": "codex-cli"},
        ),
        review_adjudication=True,
    ))

    ensemble = result.review_ensemble
    assert ensemble is not None
    assert ensemble["disagreement_count"] == 1
    assert ensemble["finding_groups"][0]["disposition"] == "unresolved_dissent"
    assert ensemble["adjudication_requested"] is True
    assert ensemble["adjudication_invoked"] is False
    assert ensemble["adjudication_completed"] is False
    assert ensemble["finding_groups"][0]["severities"] == ["high", "medium"]
    assert ensemble["provider_cost"] == {
        "observed": True,
        "observation_count": 2,
        "rejected_observation_count": 0,
        "total": 0.5,
    }


class _MalformedEnsembleInvoker(_Invoker):
    async def __call__(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool_name == "review_change_with_agent":
            self.calls.append((tool_name, arguments))
            return {
                "status": "completed",
                "backend": arguments["backend"],
                "review_type": arguments["review_type"],
                "source_fingerprint": "f" * 64,
                "evidence_complete": True,
                "summary": "malformed finding",
                "findings": [{"severity": "medium", "path": "src/example.py"}],
                "unknowns": [],
                "diagnostics": [],
            }
        return await super().__call__(tool_name, arguments)


def test_execution_fails_closed_on_malformed_ensemble_findings() -> None:
    result = asyncio.run(ChangeExecutionService(_MalformedEnsembleInvoker()).execute(
        project=r"C:\Projects\fixture",
        complexity="small",
        review_types=("code-quality",),
        reviewers=({"reviewer_id": "one", "backend": "codex-cli"},),
    ))

    assert result.status == "incomplete"
    assert result.review_error_count == 1
    assert result.reviews[0].status == "error"
    assert result.reviews[0].error_code == "AGENT_REVIEW_ENSEMBLE_RESULT_INVALID"
    assert result.review_ensemble is not None
    assert result.review_ensemble["completed_invocation_count"] == 0


class _NonObjectReviewInvoker(_Invoker):
    async def __call__(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        if tool_name == "review_change_with_agent":
            self.calls.append((tool_name, arguments))
            return ["not", "an", "object"]
        return await super().__call__(tool_name, arguments)


def test_execution_classifies_nonobject_reviewer_output_as_review_error() -> None:
    result = asyncio.run(ChangeExecutionService(_NonObjectReviewInvoker()).execute(
        project=r"C:\Projects\fixture",
        complexity="small",
        review_types=("code-quality",),
        reviewers=({"reviewer_id": "one", "backend": "codex-cli"},),
    ))
    assert result.status == "incomplete"
    assert result.review_error_count == 1
    assert result.reviews[0].error_code == "AGENT_REVIEW_ENSEMBLE_RESULT_INVALID"


class _TooManyFindingsInvoker(_Invoker):
    async def __call__(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool_name == "review_change_with_agent":
            self.calls.append((tool_name, arguments))
            finding = {
                "severity": "medium", "path": "src/example.py", "line": 1,
                "claim": "bounded claim", "evidence": "evidence",
                "recommendation": "inspect", "confidence": "high",
            }
            return {
                "status": "completed", "backend": arguments["backend"],
                "review_type": arguments["review_type"], "source_fingerprint": "f" * 64,
                "evidence_complete": True, "summary": "too many findings",
                "findings": [dict(finding) for _ in range(21)],
                "unknowns": [], "diagnostics": [],
            }
        return await super().__call__(tool_name, arguments)

def test_execution_rejects_reviewer_finding_overflow() -> None:
    result = asyncio.run(ChangeExecutionService(_TooManyFindingsInvoker()).execute(
        project=r"C:\Projects\fixture",
        complexity="small",
        review_types=("code-quality",),
        reviewers=({"reviewer_id": "one", "backend": "codex-cli"},),
    ))
    assert result.status == "incomplete"
    assert result.review_error_count == 1
    assert result.reviews[0].error_code == "AGENT_REVIEW_ENSEMBLE_RESULT_INVALID"
    assert result.review_ensemble is not None
    assert result.review_ensemble["unique_finding_count"] == 0


@pytest.mark.parametrize("reviewer_id", [None, True, 123, ["x"], {"x": "y"}])
def test_execution_rejects_nontext_reviewer_identity(reviewer_id: Any) -> None:
    invoker = _Invoker()
    with pytest.raises(TypeError, match="reviewer_id must be a string"):
        asyncio.run(ChangeExecutionService(invoker).execute(
            project=r"C:\Projects\fixture",
            reviewers=({"reviewer_id": reviewer_id, "backend": "codex-cli"},),
        ))
    assert invoker.calls == []


class _InvalidPayloadEnsembleInvoker(_Invoker):
    def __init__(self, invalid_value: Any) -> None:
        super().__init__()
        self.invalid_value = invalid_value

    async def __call__(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool_name == "review_change_with_agent":
            self.calls.append((tool_name, arguments))
            return {
                "status": "completed", "backend": arguments["backend"],
                "review_type": arguments["review_type"], "source_fingerprint": "f" * 64,
                "evidence_complete": True, "summary": "review complete",
                "findings": [], "unknowns": [], "diagnostics": [],
                "cost": self.invalid_value,
            }
        return await super().__call__(tool_name, arguments)

@pytest.mark.parametrize(
    "invalid_value",
    [object(), "x" * 70_000, float("nan"), float("inf"), float("-inf")],
    ids=("nonserializable", "oversized", "nan", "positive-inf", "negative-inf"),
)
def test_execution_omits_invalid_ensemble_payload_from_result(invalid_value: Any) -> None:
    result = asyncio.run(ChangeExecutionService(_InvalidPayloadEnsembleInvoker(invalid_value)).execute(
        project=r"C:\Projects\fixture",
        complexity="small",
        review_types=("code-quality",),
        reviewers=({"reviewer_id": "one", "backend": "codex-cli"},),
    ))
    assert result.status == "incomplete"
    assert result.review_error_count == 1
    assert result.reviews[0].payload is None
    assert result.reviews[0].error_code == "AGENT_REVIEW_ENSEMBLE_RESULT_INVALID"
    json.dumps(result.to_json_dict())


@pytest.mark.parametrize("review_rounds", [True, False])
def test_execution_rejects_boolean_review_rounds_without_ensemble(review_rounds: bool) -> None:
    invoker = _Invoker()
    with pytest.raises(TypeError, match="review_rounds must be an integer"):
        asyncio.run(ChangeExecutionService(invoker).execute(
            project=r"C:\Projects\fixture",
            review_rounds=review_rounds,
        ))
    assert invoker.calls == []


class _UnexpectedReviewerFieldInvoker(_Invoker):
    async def __call__(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool_name == "review_change_with_agent":
            self.calls.append((tool_name, arguments))
            return {
                "status": "completed", "backend": arguments["backend"],
                "review_type": arguments["review_type"], "source_fingerprint": "f" * 64,
                "evidence_complete": True, "summary": "review complete",
                "findings": [], "unknowns": [], "diagnostics": [],
                "unexpected": "value",
            }
        return await super().__call__(tool_name, arguments)


def test_execution_rejects_unknown_reviewer_result_keys() -> None:
    result = asyncio.run(ChangeExecutionService(_UnexpectedReviewerFieldInvoker()).execute(
        project=r"C:\Projects\fixture", complexity="small",
        review_types=("code-quality",),
        reviewers=({"reviewer_id": "one", "backend": "codex-cli"},),
    ))
    assert result.status == "incomplete"
    assert result.reviews[0].error_code == "AGENT_REVIEW_ENSEMBLE_RESULT_INVALID"


class _MismatchedReviewerModelInvoker(_Invoker):
    async def __call__(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool_name == "review_change_with_agent":
            self.calls.append((tool_name, arguments))
            return {
                "status": "completed", "backend": arguments["backend"],
                "review_type": arguments["review_type"], "source_fingerprint": "f" * 64,
                "evidence_complete": True, "summary": "review complete",
                "findings": [], "unknowns": [], "diagnostics": [],
                "model_profile": "super",
            }
        return await super().__call__(tool_name, arguments)


def test_execution_rejects_mismatched_reviewer_model_profile() -> None:
    result = asyncio.run(ChangeExecutionService(_MismatchedReviewerModelInvoker()).execute(
        project=r"C:\Projects\fixture", complexity="small",
        review_types=("code-quality",),
        reviewers=({"reviewer_id": "one", "backend": "nvidia-nim", "model": "nano"},),
    ))
    assert result.status == "incomplete"
    assert result.reviews[0].error_code == "AGENT_REVIEW_ENSEMBLE_RESULT_INVALID"


class _LargeFiniteCostInvoker(_Invoker):
    async def __call__(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool_name == "review_change_with_agent":
            self.calls.append((tool_name, arguments))
            return {
                "status": "completed", "backend": arguments["backend"],
                "review_type": arguments["review_type"], "source_fingerprint": "f" * 64,
                "evidence_complete": True, "summary": "review complete",
                "findings": [], "unknowns": [], "diagnostics": [],
                "cost": 1e308,
            }
        return await super().__call__(tool_name, arguments)


def test_execution_keeps_aggregate_cost_finite() -> None:
    result = asyncio.run(ChangeExecutionService(_LargeFiniteCostInvoker()).execute(
        project=r"C:\Projects\fixture", complexity="small",
        review_types=("code-quality",),
        reviewers=(
            {"reviewer_id": "one", "backend": "codex-cli"},
            {"reviewer_id": "two", "backend": "codex-cli"},
        ),
    ))
    ensemble = result.review_ensemble
    assert ensemble is not None
    assert ensemble["provider_cost"] == {
        "observed": True,
        "observation_count": 1,
        "rejected_observation_count": 1,
        "total": 1e308,
    }
    json.dumps(result.to_json_dict(), allow_nan=False)


@pytest.mark.parametrize(
    ("field", "value"),
    [("summary", 1), ("unknowns", {}), ("unknowns", [""]), ("diagnostics", "bad"), ("diagnostics", [""])],
)
def test_execution_rejects_malformed_reviewer_result_fields(field: str, value: Any) -> None:
    class _InvokerWithField(_Invoker):
        async def __call__(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
            if tool_name == "review_change_with_agent":
                self.calls.append((tool_name, arguments))
                payload = {
                    "status": "completed", "backend": arguments["backend"],
                    "review_type": arguments["review_type"], "source_fingerprint": "f" * 64,
                    "evidence_complete": True, "summary": "ok", "findings": [],
                    "unknowns": [], "diagnostics": [],
                }
                payload[field] = value
                return payload
            return await super().__call__(tool_name, arguments)

    result = asyncio.run(ChangeExecutionService(_InvokerWithField()).execute(
        project=r"C:\Projects\fixture", complexity="small", review_types=("code-quality",),
        reviewers=({"reviewer_id": "one", "backend": "codex-cli"},),
    ))
    assert result.status == "incomplete"
    assert result.reviews[0].error_code == "AGENT_REVIEW_ENSEMBLE_RESULT_INVALID"


def test_execution_rejects_unknown_reviewer_profile_key() -> None:
    invoker = _Invoker()
    with pytest.raises(ValueError, match="reviewer profile keys"):
        asyncio.run(ChangeExecutionService(invoker).execute(
            project=r"C:\Projects\fixture",
            reviewers=({"reviewer_id": "one", "backend": "codex-cli", "extra": True},),
        ))
    assert invoker.calls == []


class _ContradictoryNvidiaModelInvoker(_Invoker):
    async def __call__(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool_name == "review_change_with_agent":
            self.calls.append((tool_name, arguments))
            return {
                "status": "completed", "backend": "nvidia-nim", "review_type": arguments["review_type"],
                "source_fingerprint": "f" * 64, "evidence_complete": True, "summary": "ok",
                "findings": [], "unknowns": [], "diagnostics": [],
                "model_profile": "nano", "model": "nvidia/not-the-requested-model",
            }
        return await super().__call__(tool_name, arguments)


def test_execution_rejects_contradictory_resolved_nvidia_model() -> None:
    result = asyncio.run(ChangeExecutionService(_ContradictoryNvidiaModelInvoker()).execute(
        project=r"C:\Projects\fixture", complexity="small", review_types=("code-quality",),
        reviewers=({"reviewer_id": "one", "backend": "nvidia-nim", "model": "nano"},),
    ))
    assert result.status == "incomplete"
    assert result.reviews[0].error_code == "AGENT_REVIEW_ENSEMBLE_RESULT_INVALID"


@pytest.mark.parametrize("mode", ["failed", "incomplete-evidence", "source-mismatch"])
def test_execution_omits_unsafe_payload_on_reviewer_error_paths(mode: str) -> None:
    class _UnsafeErrorInvoker(_Invoker):
        async def __call__(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
            if tool_name == "review_change_with_agent":
                self.calls.append((tool_name, arguments))
                payload: dict[str, Any] = {
                    "status": "completed", "backend": arguments["backend"],
                    "review_type": arguments["review_type"], "source_fingerprint": "f" * 64,
                    "evidence_complete": True, "summary": "error path", "findings": [],
                    "unknowns": [], "diagnostics": [], "unsafe": object(),
                }
                if mode == "failed":
                    payload["status"] = "failed"
                elif mode == "incomplete-evidence":
                    payload["evidence_complete"] = False
                else:
                    payload["source_fingerprint"] = "a" * 64
                return payload
            return await super().__call__(tool_name, arguments)

    result = asyncio.run(ChangeExecutionService(_UnsafeErrorInvoker()).execute(
        project=r"C:\Projects\fixture", complexity="small", review_types=("code-quality",),
        reviewers=({"reviewer_id": "one", "backend": "codex-cli"},),
    ))
    assert result.status == "incomplete"
    assert result.reviews[0].payload is None
    assert result.reviews[0].error_code == "AGENT_REVIEW_ENSEMBLE_RESULT_INVALID"
    json.dumps(result.to_json_dict(), allow_nan=False)


class _ResolvedDefaultNvidiaInvoker(_Invoker):
    def __init__(self, *, model_profile: str = "super", model: str = "nvidia/nemotron-3-super-120b-a12b") -> None:
        super().__init__()
        self.model_profile = model_profile
        self.model = model

    async def __call__(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool_name == "review_change_with_agent":
            self.calls.append((tool_name, arguments))
            return {
                "status": "completed", "backend": "nvidia-nim", "review_type": arguments["review_type"],
                "source_fingerprint": "f" * 64, "evidence_complete": True, "summary": "ok",
                "findings": [], "unknowns": [], "diagnostics": [],
                "model_profile": self.model_profile, "model": self.model,
            }
        return await super().__call__(tool_name, arguments)


def test_execution_accepts_valid_resolved_default_nvidia_model() -> None:
    result = asyncio.run(ChangeExecutionService(_ResolvedDefaultNvidiaInvoker()).execute(
        project=r"C:\Projects\fixture", complexity="small", review_types=("code-quality",),
        reviewers=({"reviewer_id": "one", "backend": "nvidia-nim"},),
    ))
    assert result.status == "passed"


def test_execution_rejects_contradictory_default_nvidia_model() -> None:
    result = asyncio.run(ChangeExecutionService(_ResolvedDefaultNvidiaInvoker(model="nvidia/wrong")).execute(
        project=r"C:\Projects\fixture", complexity="small", review_types=("code-quality",),
        reviewers=({"reviewer_id": "one", "backend": "nvidia-nim"},),
    ))
    assert result.status == "incomplete"
    assert result.reviews[0].error_code == "AGENT_REVIEW_ENSEMBLE_RESULT_INVALID"


class _ContradictorySourceInvoker(_Invoker):
    async def __call__(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool_name == "review_change_with_agent":
            self.calls.append((tool_name, arguments))
            return {
                "status": "completed", "backend": arguments["backend"],
                "review_type": arguments["review_type"], "source": "commit",
                "source_fingerprint": "f" * 64, "evidence_complete": True,
                "summary": "wrong source metadata", "findings": [],
                "unknowns": [], "diagnostics": [],
            }
        return await super().__call__(tool_name, arguments)


def test_execution_rejects_contradictory_reviewer_source_metadata() -> None:
    result = asyncio.run(ChangeExecutionService(_ContradictorySourceInvoker()).execute(
        project=r"C:\Projects\fixture", complexity="small", review_types=("code-quality",),
        reviewers=({"reviewer_id": "one", "backend": "codex-cli"},),
    ))
    assert result.status == "incomplete"
    assert result.reviews[0].error_code == "AGENT_REVIEW_ENSEMBLE_RESULT_INVALID"


class _SlowEnsembleInvoker(_Invoker):
    async def __call__(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool_name == "review_change_with_agent":
            self.calls.append((tool_name, arguments))
            await asyncio.sleep(0.05)
            return {
                "status": "completed", "backend": arguments["backend"],
                "review_type": arguments["review_type"], "source_fingerprint": "f" * 64,
                "evidence_complete": True, "summary": "late", "findings": [],
                "unknowns": [], "diagnostics": [],
            }
        return await super().__call__(tool_name, arguments)


def test_execution_ensemble_invocation_count_tracks_actual_calls() -> None:
    invoker = _SlowEnsembleInvoker()
    result = asyncio.run(ChangeExecutionService(invoker).execute(
        project=r"C:\Projects\fixture", complexity="small",
        review_types=("code-quality", "safety-security"),
        reviewers=({"reviewer_id": "one", "backend": "codex-cli"},),
        review_timeout_ms=10,
    ))
    ensemble = result.review_ensemble
    assert ensemble is not None
    assert ensemble["planned_invocation_count"] == 2
    assert ensemble["invocation_count"] == 1
    assert len([name for name, _ in invoker.calls if name == "review_change_with_agent"]) == 1


@pytest.mark.parametrize("invalid_cost", ["1.0", True, -0.01])
def test_execution_rejects_invalid_provider_cost_contract(invalid_cost: Any) -> None:
    result = asyncio.run(ChangeExecutionService(_InvalidPayloadEnsembleInvoker(invalid_cost)).execute(
        project=r"C:\Projects\fixture", complexity="small", review_types=("code-quality",),
        reviewers=({"reviewer_id": "one", "backend": "codex-cli"},),
    ))
    assert result.status == "incomplete"
    assert result.review_error_count == 1
    assert result.reviews[0].error_code == "AGENT_REVIEW_ENSEMBLE_RESULT_INVALID"
    assert result.reviews[0].payload is None


def test_execution_omits_serializable_payload_on_failed_reviewer_result() -> None:
    class _FailedInvoker(_Invoker):
        async def __call__(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
            if tool_name == "review_change_with_agent":
                self.calls.append((tool_name, arguments))
                return {
                    "status": "failed", "backend": arguments["backend"],
                    "review_type": arguments["review_type"], "source_fingerprint": "f" * 64,
                    "evidence_complete": True, "summary": "provider failed", "findings": [],
                    "unknowns": [], "diagnostics": ["PROVIDER_FAILED"],
                    "unexpected_sensitive_field": "must-not-be-retained",
                }
            return await super().__call__(tool_name, arguments)

    result = asyncio.run(ChangeExecutionService(_FailedInvoker()).execute(
        project=r"C:\Projects\fixture", complexity="small", review_types=("code-quality",),
        reviewers=({"reviewer_id": "one", "backend": "codex-cli"},),
    ))
    assert result.status == "incomplete"
    assert result.reviews[0].payload is None


@pytest.mark.parametrize(
    ("field", "request_value", "result_value"),
    [
        ("commit_ref", "abc123", "def456"),
        ("base_ref", "main", "release"),
        ("head_ref", "feature", "other"),
    ],
)
def test_execution_rejects_contradictory_source_ref_metadata(
    field: str, request_value: str, result_value: str
) -> None:
    class _RefInvoker(_Invoker):
        async def __call__(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
            if tool_name == "review_change_with_agent":
                self.calls.append((tool_name, arguments))
                return {
                    "status": "completed", "backend": arguments["backend"],
                    "review_type": arguments["review_type"], "source_fingerprint": "f" * 64,
                    "evidence_complete": True, "summary": "wrong ref", "findings": [],
                    "unknowns": [], "diagnostics": [], field: result_value,
                }
            return await super().__call__(tool_name, arguments)

    kwargs = {field: request_value}
    result = asyncio.run(ChangeExecutionService(_RefInvoker()).execute(
        project=r"C:\Projects\fixture", complexity="small", review_types=("code-quality",),
        reviewers=({"reviewer_id": "one", "backend": "codex-cli"},), **kwargs,
    ))
    assert result.status == "incomplete"
    assert result.reviews[0].error_code == "AGENT_REVIEW_ENSEMBLE_RESULT_INVALID"


def test_execution_rejects_provider_supplied_ensemble_provenance() -> None:
    class _ProviderProvenanceInvoker(_Invoker):
        async def __call__(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
            if tool_name == "review_change_with_agent":
                self.calls.append((tool_name, arguments))
                return {
                    "status": "completed", "backend": arguments["backend"],
                    "review_type": arguments["review_type"], "source_fingerprint": "f" * 64,
                    "evidence_complete": True, "summary": "contradictory provenance",
                    "findings": [], "unknowns": [], "diagnostics": [],
                    "ensemble_provenance": {"reviewer_id": "spoofed"},
                }
            return await super().__call__(tool_name, arguments)

    result = asyncio.run(ChangeExecutionService(_ProviderProvenanceInvoker()).execute(
        project=r"C:\Projects\fixture", complexity="small", review_types=("code-quality",),
        reviewers=({"reviewer_id": "one", "backend": "codex-cli"},),
    ))
    assert result.status == "incomplete"
    assert result.reviews[0].payload is None
    assert result.reviews[0].error_code == "AGENT_REVIEW_ENSEMBLE_RESULT_INVALID"
