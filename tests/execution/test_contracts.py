from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from kis_mcp.execution.contracts import (
    CleanupDisposition,
    ExecutionEvidence,
    ExecutionProfile,
    ExecutionRequest,
    ExecutionResult,
    ExecutionSource,
)


def _request(*, exact: bool = True) -> ExecutionRequest:
    return ExecutionRequest(
        request_id="proof-001",
        project_id="kis-mcp",
        verification_profile_id="python",
        source=ExecutionSource(
            project_path=r"C:\Projects\kis-mcp",
            revision="9adf1ca26a6a96a173605a7e5dd5c11216d6ec0e" if exact else "working-tree",
            exact=exact,
        ),
        profile=ExecutionProfile(
            profile_id="windows-proof",
            backend_id="windows-hyperv",
            image_id="win11-kis-v1",
            toolchain_id="python-3.13",
        ),
        executable="python",
        arguments=("-m", "pytest", "-q"),
        timeout_ms=120_000,
        evidence_limit_chars=20_000,
    )


def test_execution_contract_is_immutable_and_json_stable() -> None:
    request = _request()
    with pytest.raises(FrozenInstanceError):
        request.timeout_ms = 1  # type: ignore[misc]

    payload = request.to_json_dict()
    assert payload["contract"] == "execution-request-v1"
    assert payload["source"]["exact"] is True
    assert payload["profile"]["backend_id"] == "windows-hyperv"
    assert payload["arguments"] == ["-m", "pytest", "-q"]


def test_exact_source_requires_lowercase_git_commit_identity() -> None:
    with pytest.raises(ValueError, match="40 lowercase hex"):
        ExecutionSource(
            project_path=r"C:\Projects\kis-mcp",
            revision="HEAD",
            exact=True,
        )


def test_result_cannot_report_passed_without_complete_lifecycle() -> None:
    request = _request()
    with pytest.raises(ValueError, match="passed execution requires"):
        ExecutionResult(
            request_id=request.request_id,
            backend_id=request.profile.backend_id,
            status="passed",
            exit_code=0,
            duration_ms=10,
            source_revision=request.source.revision,
            image_id=request.profile.image_id,
            toolchain_id=request.profile.toolchain_id,
            cleanup=CleanupDisposition.FAILED,
            evidence=ExecutionEvidence(stdout="ok"),
            failure_classification="none",
        )
