from __future__ import annotations

from dataclasses import replace

import pytest

import kis_mcp.work_management as work_management
from kis_mcp.work_management import (
    DocumentationImpact,
    DocumentationMilestoneState,
    DocumentationMode,
    LifecycleState,
    RecordType,
    WorkRecord,
)
from kis_mcp.work_management.traceability import (
    CloseoutEvidence,
    DocumentationReconciliationEvent,
    ImplementationTrace,
    MergeEvidence,
    PullRequestEvidence,
    PullRequestState,
    TraceabilityIssueKind,
    TraceabilityStage,
    VerificationEvidence,
    VerificationStatus,
    apply_documentation_reconciliation_event,
    complete_documentation_reconciliation,
    create_documentation_reconciliation_due,
    evaluate_merge_readiness,
    evaluate_traceability,
)


def revision(character: str) -> str:
    return character * 40


def record(**overrides: object) -> WorkRecord:
    values: dict[str, object] = {
        "record_id": "SPEC-053",
        "project_id": "kis-mcp",
        "title": "Implementation traceability",
        "record_type": RecordType.SPECIFICATION_SLICE,
        "state": LifecycleState.VERIFICATION,
        "documentation_mode": DocumentationMode.REQUIRED,
        "documentation_impact": DocumentationImpact.PRE_MERGE_COMPLETE,
        "traceability_required": True,
    }
    values.update(overrides)
    return WorkRecord(**values)  # type: ignore[arg-type]


def pull_request(
    *,
    number: int = 63,
    head_revision: str | None = None,
    head_branch: str = "change/053-work-management-traceability",
    state: PullRequestState = PullRequestState.OPEN,
) -> PullRequestEvidence:
    return PullRequestEvidence(
        repository="NielPieterse0/kis-mcp",
        number=number,
        head_branch=head_branch,
        head_revision=head_revision or revision("a"),
        base_branch="main",
        state=state,
    )


def trace(
    *,
    prs: tuple[PullRequestEvidence, ...] | None = None,
    verifications: tuple[VerificationEvidence, ...] = (),
    merges: tuple[MergeEvidence, ...] = (),
    closeout: CloseoutEvidence | None = None,
    documentation_events: tuple[DocumentationReconciliationEvent, ...] = (),
    branch: str | None = "change/053-work-management-traceability",
    worktree: str | None = ".work/worktrees/053-work-management-traceability",
) -> ImplementationTrace:
    return ImplementationTrace(
        project_id="kis-mcp",
        specification_record_id="SPEC-053",
        change_id="053-work-management-traceability",
        branch=branch,
        worktree=worktree,
        pull_requests=prs if prs is not None else (pull_request(),),
        verifications=verifications,
        merges=merges,
        closeout=closeout,
        documentation_events=documentation_events,
    )


def test_traceability_evidence_contracts_are_json_safe() -> None:
    pr = pull_request()
    verification = VerificationEvidence(
        evidence_id="verify-053-head",
        pull_request_number=63,
        revision=pr.head_revision,
        status=VerificationStatus.PASSED,
        command="pwsh -NoProfile -File scripts/verify.ps1",
        source="local",
    )
    merge = MergeEvidence(
        pull_request_number=63,
        merge_commit=revision("b"),
        head_revision=pr.head_revision,
    )
    closeout = CloseoutEvidence(
        path=".work/changes/053-work-management-traceability/closeout.md",
        revision=revision("c"),
    )
    value = trace(
        prs=(pr,),
        verifications=(verification,),
        merges=(merge,),
        closeout=closeout,
    )

    payload = value.to_json_dict()

    assert payload["change_id"] == "053-work-management-traceability"
    assert payload["pull_requests"][0]["number"] == 63
    assert payload["verifications"][0]["status"] == "passed"
    assert payload["merges"][0]["merge_commit"] == revision("b")
    assert payload["closeout"]["path"].endswith("closeout.md")


def test_traceability_contracts_reject_invalid_identity() -> None:
    with pytest.raises(ValueError, match="change_id"):
        ImplementationTrace(
            project_id="kis-mcp",
            specification_record_id="SPEC-053",
            change_id="traceability",
            branch=None,
            worktree=None,
        )

    with pytest.raises(ValueError, match="revision"):
        VerificationEvidence(
            evidence_id="verify-1",
            pull_request_number=63,
            revision="not-a-commit",
            status=VerificationStatus.PASSED,
            command="verify",
        )


def verification(
    *,
    evidence_id: str = "verify-053-head",
    pull_request_number: int = 63,
    tested_revision: str | None = None,
    status: VerificationStatus = VerificationStatus.PASSED,
    source: str = "local",
    reference: str | None = None,
) -> VerificationEvidence:
    return VerificationEvidence(
        evidence_id=evidence_id,
        pull_request_number=pull_request_number,
        revision=tested_revision or revision("a"),
        status=status,
        command="pwsh -NoProfile -File scripts/verify.ps1",
        source=source,
        reference=reference,
    )


def issue_codes(report: object) -> set[str]:
    return {issue.code for issue in report.issues}  # type: ignore[attr-defined]


def test_active_traceability_reports_missing_and_contradictory_core_links() -> None:
    value = ImplementationTrace(
        project_id="kis-mcp",
        specification_record_id=None,
        change_id="053-work-management-traceability",
        branch="change/other-change",
        worktree=".work/worktrees/other-change",
    )

    report = evaluate_traceability(value, TraceabilityStage.ACTIVE)

    assert report.valid is False
    assert issue_codes(report) == {
        "missing_specification_record",
        "branch_change_mismatch",
        "worktree_change_mismatch",
    }


def test_review_and_merge_ready_require_pr_and_exact_verification() -> None:
    review_report = evaluate_traceability(
        trace(prs=()),
        TraceabilityStage.REVIEW,
        pull_request_number=63,
    )
    stale_report = evaluate_traceability(
        trace(
            verifications=(
                verification(tested_revision=revision("d")),
            )
        ),
        TraceabilityStage.MERGE_READY,
        pull_request_number=63,
    )

    assert issue_codes(review_report) == {"missing_pull_request"}
    assert {
        "verification_revision_stale",
        "missing_passing_verification",
    }.issubset(issue_codes(stale_report))
    stale = next(
        issue
        for issue in stale_report.issues
        if issue.code == "verification_revision_stale"
    )
    assert stale.kind is TraceabilityIssueKind.STALE


def test_traceability_reports_duplicate_evidence() -> None:
    pr = pull_request()
    verify = verification()
    merge = MergeEvidence(
        pull_request_number=63,
        merge_commit=revision("b"),
        head_revision=pr.head_revision,
    )
    event = DocumentationReconciliationEvent(
        event_id="doc-053-pr-63",
        project_id="kis-mcp",
        specification_record_id="SPEC-053",
        change_id="053-work-management-traceability",
        pull_request_number=63,
        merge_commit=merge.merge_commit,
        documentation_task_id="TASK-053",
        required_updates=("Reconcile closeout",),
        state=DocumentationMilestoneState.DOCUMENTATION_RECONCILIATION_DUE,
    )
    report = evaluate_traceability(
        trace(
            prs=(pr, pr),
            verifications=(verify, verify),
            merges=(merge, merge),
            documentation_events=(event, event),
        ),
        TraceabilityStage.CLOSED,
        pull_request_number=63,
    )

    assert {
        "duplicate_pull_request",
        "duplicate_verification",
        "duplicate_merge",
        "duplicate_documentation_event",
    }.issubset(issue_codes(report))
    duplicate_kinds = {
        issue.kind
        for issue in report.issues
        if issue.code.startswith("duplicate_")
    }
    assert duplicate_kinds == {TraceabilityIssueKind.DUPLICATED}


def test_traceability_reports_orphaned_and_mismatched_relationships() -> None:
    pr = pull_request(head_branch="change/wrong-branch")
    orphan_verification = verification(pull_request_number=99)
    orphan_merge = MergeEvidence(
        pull_request_number=99,
        merge_commit=revision("b"),
        head_revision=revision("e"),
    )
    report = evaluate_traceability(
        trace(
            prs=(pr,),
            verifications=(orphan_verification,),
            merges=(orphan_merge,),
            closeout=CloseoutEvidence(
                path=".work/changes/053-work-management-traceability/closeout.md",
                revision=revision("c"),
            ),
        ),
        TraceabilityStage.MERGED,
        pull_request_number=63,
    )

    assert {
        "pull_request_branch_mismatch",
        "orphan_verification",
        "orphan_merge",
        "missing_merge",
    }.issubset(issue_codes(report))


def merge_ready_trace(
    *,
    tested_revision: str | None = None,
    status: VerificationStatus = VerificationStatus.PASSED,
) -> ImplementationTrace:
    pr = pull_request()
    return trace(
        prs=(pr,),
        verifications=(
            verification(
                tested_revision=tested_revision or pr.head_revision,
                status=status,
                source="github_actions",
                reference="run:1001",
            ),
        ),
    )


def test_merge_readiness_requires_exact_revision_and_matching_identity() -> None:
    ready = evaluate_merge_readiness(record(), merge_ready_trace(), 63)
    stale = evaluate_merge_readiness(
        record(),
        merge_ready_trace(tested_revision=revision("d")),
        63,
    )
    mismatched = evaluate_merge_readiness(
        record(project_id="other-project"),
        merge_ready_trace(),
        63,
    )

    assert ready.ready is True
    assert ready.blocking_reasons == ()
    assert stale.ready is False
    assert "traceability:verification_revision_stale" in stale.blocking_reasons
    assert "record_project_mismatch" in mismatched.blocking_reasons


def test_merge_readiness_requires_provider_native_github_actions_evidence() -> None:
    pr = pull_request()
    local_only = trace(
        prs=(pr,),
        verifications=(verification(tested_revision=pr.head_revision),),
    )

    readiness = evaluate_merge_readiness(record(), local_only, pr.number)

    assert readiness.ready is False
    assert "github_actions_exact_head_required" in readiness.blocking_reasons


def test_required_documentation_must_be_pre_merge_complete_or_reviewed_none() -> None:
    incomplete = evaluate_merge_readiness(
        record(documentation_impact=DocumentationImpact.PLANNED),
        merge_ready_trace(),
        63,
    )
    reviewed_none = evaluate_merge_readiness(
        record(
            documentation_impact=DocumentationImpact.NONE,
            documentation_rationale="No reader-facing behavior changed",
            documentation_reviewer="operator",
        ),
        merge_ready_trace(),
        63,
    )

    assert incomplete.ready is False
    assert incomplete.blocking_reasons == ("documentation_pre_merge_incomplete",)
    assert reviewed_none.ready is True


def test_advisory_and_off_documentation_modes_do_not_block_merge() -> None:
    advisory = evaluate_merge_readiness(
        record(
            documentation_mode=DocumentationMode.ADVISORY,
            documentation_impact=DocumentationImpact.PLANNED,
        ),
        merge_ready_trace(),
        63,
    )
    off = evaluate_merge_readiness(
        record(
            documentation_mode=DocumentationMode.OFF,
            documentation_impact=DocumentationImpact.NOT_ASSESSED,
        ),
        merge_ready_trace(),
        63,
    )

    assert advisory.ready is True
    assert advisory.advisories == ("documentation_pre_merge_advisory_incomplete",)
    assert off.ready is True
    assert off.advisories == ()


def merged_trace() -> ImplementationTrace:
    pr = pull_request(state=PullRequestState.MERGED)
    merge = MergeEvidence(
        pull_request_number=pr.number,
        merge_commit=revision("b"),
        head_revision=pr.head_revision,
    )
    return trace(
        prs=(pr,),
        verifications=(verification(),),
        merges=(merge,),
    )


def test_merge_creates_due_documentation_event_and_updates_lifecycle() -> None:
    event = create_documentation_reconciliation_due(
        merged_trace(),
        63,
        "TASK-053",
        ("Reconcile closeout", "Update programme status"),
    )

    assert event.event_id == "doc-053-work-management-traceability-pr-63"
    assert event.state is (
        DocumentationMilestoneState.DOCUMENTATION_RECONCILIATION_DUE
    )
    assert event.merge_commit == revision("b")
    assert event.documentation_task_id == "TASK-053"

    updated = apply_documentation_reconciliation_event(record(), event)

    assert updated.state is LifecycleState.DOCUMENTATION
    assert updated.traceability_required is True
    assert updated.documentation_milestone is (
        DocumentationMilestoneState.DOCUMENTATION_RECONCILIATION_DUE
    )
    assert updated.documentation_event_id == event.event_id


def test_completed_documentation_event_allows_traceability_closeout() -> None:
    base_trace = merged_trace()
    due = create_documentation_reconciliation_due(
        base_trace,
        63,
        "TASK-053",
        ("Reconcile closeout",),
    )
    current = apply_documentation_reconciliation_event(record(), due)
    completed = complete_documentation_reconciliation(due, revision("c"))
    reconciled = apply_documentation_reconciliation_event(current, completed)
    closed_trace = replace(
        base_trace,
        closeout=CloseoutEvidence(
            path=".work/changes/053-work-management-traceability/closeout.md",
            revision=revision("d"),
        ),
        documentation_events=(completed,),
    )

    report = evaluate_traceability(
        closed_trace,
        TraceabilityStage.CLOSED,
        pull_request_number=63,
    )

    assert reconciled.documentation_impact is DocumentationImpact.POST_MERGE_COMPLETE
    assert reconciled.documentation_milestone is (
        DocumentationMilestoneState.POST_MERGE_COMPLETE
    )
    assert report.valid is True


def test_documentation_event_rejects_missing_merge_and_identity_mismatch() -> None:
    with pytest.raises(ValueError, match="merge evidence"):
        create_documentation_reconciliation_due(
            trace(),
            63,
            "TASK-053",
            ("Reconcile closeout",),
        )

    event = create_documentation_reconciliation_due(
        merged_trace(),
        63,
        "TASK-053",
        ("Reconcile closeout",),
    )
    mismatched = replace(event, project_id="other-project")

    with pytest.raises(ValueError, match="identity"):
        apply_documentation_reconciliation_event(record(), mismatched)


def test_traceability_contracts_are_exported_from_domain_package() -> None:
    assert work_management.ImplementationTrace is ImplementationTrace
    assert work_management.evaluate_traceability is evaluate_traceability
    assert work_management.evaluate_merge_readiness is evaluate_merge_readiness
    assert (
        work_management.create_documentation_reconciliation_due
        is create_documentation_reconciliation_due
    )


def test_historical_verification_does_not_block_current_exact_pass() -> None:
    pr = pull_request()
    value = trace(
        prs=(pr,),
        verifications=(
            verification(
                evidence_id="verify-old",
                tested_revision=revision("d"),
            ),
            verification(
                evidence_id="verify-current",
                tested_revision=pr.head_revision,
                source="github_actions",
                reference="run:current",
            ),
        ),
    )

    readiness = evaluate_merge_readiness(record(), value, 63)

    assert readiness.ready is True
    assert "traceability:verification_revision_stale" not in (
        readiness.blocking_reasons
    )


def test_merge_evidence_requires_merged_pull_request_state() -> None:
    pr = pull_request(state=PullRequestState.OPEN)
    value = trace(
        prs=(pr,),
        verifications=(verification(),),
        merges=(
            MergeEvidence(
                pull_request_number=63,
                merge_commit=revision("b"),
                head_revision=pr.head_revision,
            ),
        ),
    )

    report = evaluate_traceability(
        value,
        TraceabilityStage.MERGED,
        pull_request_number=63,
    )

    assert "merge_pull_request_state_mismatch" in issue_codes(report)


def test_trace_requires_specification_slice_identity() -> None:
    with pytest.raises(ValueError, match="SPEC"):
        ImplementationTrace(
            project_id="kis-mcp",
            specification_record_id="TASK-053",
            change_id="053-work-management-traceability",
            branch="change/053-work-management-traceability",
            worktree=".work/worktrees/053-work-management-traceability",
        )


def test_closeout_path_must_match_change_identity() -> None:
    value = replace(
        merged_trace(),
        closeout=CloseoutEvidence(
            path=".work/changes/999-other/closeout.md",
            revision=revision("c"),
        ),
    )

    report = evaluate_traceability(
        value,
        TraceabilityStage.MERGED,
        pull_request_number=63,
    )

    assert "closeout_path_mismatch" in issue_codes(report)


def test_traceability_results_are_json_safe() -> None:
    readiness = evaluate_merge_readiness(record(), merge_ready_trace(), 63)

    payload = readiness.to_json_dict()

    assert payload["ready"] is True
    assert payload["traceability"]["stage"] == "merge_ready"
    assert payload["traceability"]["issues"] == []


def test_merge_ready_requires_open_pull_request_state() -> None:
    pr = pull_request(state=PullRequestState.MERGED)
    value = trace(
        prs=(pr,),
        verifications=(verification(),),
    )

    report = evaluate_traceability(
        value,
        TraceabilityStage.MERGE_READY,
        pull_request_number=63,
    )

    assert "pull_request_state_not_open" in issue_codes(report)


def test_semantic_duplicate_verification_is_detected_across_evidence_ids() -> None:
    value = trace(
        verifications=(
            verification(evidence_id="verify-import-1"),
            verification(evidence_id="verify-import-2"),
        )
    )

    report = evaluate_traceability(
        value,
        TraceabilityStage.MERGE_READY,
        pull_request_number=63,
    )

    assert "duplicate_verification" in issue_codes(report)


def test_completed_documentation_event_must_match_due_event_identity() -> None:
    base_trace = merged_trace()
    due = create_documentation_reconciliation_due(
        base_trace,
        63,
        "TASK-053",
        ("Reconcile closeout",),
    )
    current = apply_documentation_reconciliation_event(record(), due)
    different_event = replace(
        complete_documentation_reconciliation(due, revision("c")),
        event_id="doc-different-pr-63",
    )

    with pytest.raises(ValueError, match="event identity"):
        apply_documentation_reconciliation_event(current, different_event)
