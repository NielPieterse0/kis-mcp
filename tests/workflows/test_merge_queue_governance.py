from __future__ import annotations

import pytest
from fastmcp.exceptions import ToolError

from kis_mcp.work_management import (
    DocumentationImpact,
    DocumentationMode,
    LifecycleState,
    RecordType,
    WorkRecord,
)
from kis_mcp.work_management.traceability import (
    ImplementationTrace,
    PullRequestEvidence,
    PullRequestState,
    VerificationEvidence,
    VerificationStatus,
)
from kis_mcp.workflows.merge_queue import _governance_receipt

HEAD = "a" * 40


def record_json() -> dict[str, object]:
    return WorkRecord(
        record_id="SPEC-120",
        project_id="kis-mcp",
        title="KIS speculative landing queue",
        record_type=RecordType.SPECIFICATION_SLICE,
        state=LifecycleState.VERIFICATION,
        documentation_mode=DocumentationMode.REQUIRED,
        documentation_impact=DocumentationImpact.PRE_MERGE_COMPLETE,
        traceability_required=True,
    ).to_json_dict()


def trace_json(*, head: str = HEAD, github_actions: bool = True) -> dict[str, object]:
    pr = PullRequestEvidence(
        repository="NielPieterse0/kis-mcp",
        number=167,
        head_branch="change/120-kis-speculative-landing-queue",
        head_revision=head,
        base_branch="main",
        state=PullRequestState.OPEN,
    )
    verification = VerificationEvidence(
        evidence_id="verify-120-head",
        pull_request_number=167,
        revision=head,
        status=VerificationStatus.PASSED,
        command="pwsh -NoProfile -File scripts/verify.ps1",
        source="github_actions" if github_actions else "local",
        reference="run:120" if github_actions else None,
    )
    return ImplementationTrace(
        project_id="kis-mcp",
        specification_record_id="SPEC-120",
        change_id="120-kis-speculative-landing-queue",
        branch="change/120-kis-speculative-landing-queue",
        worktree=".work/worktrees/120-kis-speculative-landing-queue",
        pull_requests=(pr,),
        verifications=(verification,),
    ).to_json_dict()


def test_governance_receipt_requires_exact_ready_work_management_evidence() -> None:
    receipt = _governance_receipt("kis-mcp", 167, HEAD, record_json(), trace_json())
    assert receipt["ready"] is True
    assert receipt["record_id"] == "SPEC-120"
    assert receipt["pull_number"] == 167
    assert receipt["head_sha"] == HEAD
    assert len(receipt["evidence_sha256"]) == 64


def test_governance_receipt_rejects_stale_head_identity() -> None:
    with pytest.raises(ToolError, match="MERGE_QUEUE_GOVERNANCE_HEAD_MISMATCH"):
        _governance_receipt("kis-mcp", 167, "b" * 40, record_json(), trace_json())


def test_governance_receipt_requires_exact_github_actions_readiness() -> None:
    with pytest.raises(ToolError, match="MERGE_QUEUE_GOVERNANCE_NOT_READY"):
        _governance_receipt(
            "kis-mcp", 167, HEAD, record_json(), trace_json(github_actions=False)
        )
