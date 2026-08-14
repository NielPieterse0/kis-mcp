from __future__ import annotations

from dataclasses import replace

import pytest

from kis_mcp.work_management import (
    DocumentationImpact,
    DocumentationMilestoneState,
    DocumentationMode,
    LifecycleState,
    RecordType,
    TransitionRejected,
    WorkRecord,
    evaluate_transition,
    load_command_plane_settings,
    transition_record,
)


def record(**overrides: object) -> WorkRecord:
    values: dict[str, object] = {
        "record_id": "TASK-001",
        "project_id": "alpha-project",
        "title": "Complete the slice",
        "record_type": RecordType.TASK,
        "state": LifecycleState.APPROVED,
    }
    values.update(overrides)
    return WorkRecord(**values)  # type: ignore[arg-type]


def test_active_to_done_is_allowed_by_policy_but_guarded_by_closeout() -> None:
    decision = evaluate_transition(
        record(state=LifecycleState.ACTIVE), LifecycleState.DONE
    )

    assert decision.allowed is False
    assert decision.reasons == ("documentation_incomplete",)


def test_approved_work_can_move_to_ready() -> None:
    updated = transition_record(record(), LifecycleState.READY)
    assert updated.state is LifecycleState.READY


def test_activation_requires_completed_approval() -> None:
    decision = evaluate_transition(
        record(approval_required=True, approval_complete=False),
        LifecycleState.ACTIVE,
    )

    assert decision.allowed is False
    assert decision.reasons == ("approval_incomplete",)


def test_required_documentation_blocks_done_until_post_merge() -> None:
    current = record(
        state=LifecycleState.DOCUMENTATION,
        documentation_mode=DocumentationMode.REQUIRED,
        documentation_impact=DocumentationImpact.PRE_MERGE_COMPLETE,
    )

    with pytest.raises(TransitionRejected, match="documentation_incomplete"):
        transition_record(current, LifecycleState.DONE)


def test_no_impact_with_review_evidence_satisfies_required_documentation() -> None:
    current = record(
        state=LifecycleState.DOCUMENTATION,
        documentation_mode=DocumentationMode.REQUIRED,
        documentation_impact=DocumentationImpact.NONE,
        documentation_rationale="No reader-facing behavior changed",
        documentation_reviewer="operator",
    )

    updated = transition_record(current, LifecycleState.DONE)

    assert updated.state is LifecycleState.DONE


def test_post_merge_documentation_allows_done() -> None:
    current = record(
        state=LifecycleState.DOCUMENTATION,
        documentation_mode=DocumentationMode.REQUIRED,
        documentation_impact=DocumentationImpact.POST_MERGE_COMPLETE,
    )

    assert transition_record(current, LifecycleState.DONE).state is LifecycleState.DONE


def test_advisory_documentation_allows_done_with_reason() -> None:
    current = record(
        state=LifecycleState.DOCUMENTATION,
        documentation_mode=DocumentationMode.ADVISORY,
        documentation_impact=DocumentationImpact.PLANNED,
    )

    decision = evaluate_transition(current, LifecycleState.DONE)

    assert decision.allowed is True
    assert decision.reasons == ("documentation_advisory_incomplete",)


def test_active_record_can_be_superseded() -> None:
    current = record(state=LifecycleState.ACTIVE)

    updated = transition_record(current, LifecycleState.SUPERSEDED)

    assert updated.state is LifecycleState.SUPERSEDED


def test_superseded_record_is_terminal() -> None:
    decision = evaluate_transition(
        record(state=LifecycleState.SUPERSEDED), LifecycleState.ACTIVE
    )

    assert decision.allowed is False
    assert decision.reasons == ("transition_not_declared",)


def test_traceability_due_blocks_done() -> None:
    current = record(
        state=LifecycleState.DOCUMENTATION,
        traceability_required=True,
        documentation_impact=DocumentationImpact.PRE_MERGE_COMPLETE,
        documentation_milestone=(
            DocumentationMilestoneState.DOCUMENTATION_RECONCILIATION_DUE
        ),
        documentation_event_id="doc-053-pr-63",
    )

    decision = evaluate_transition(current, LifecycleState.DONE)

    assert decision.allowed is False
    assert decision.reasons == ("documentation_reconciliation_due",)


def test_traceability_requires_recorded_post_merge_reconciliation() -> None:
    current = record(
        state=LifecycleState.DOCUMENTATION,
        traceability_required=True,
        documentation_impact=DocumentationImpact.NONE,
        documentation_rationale="No reader-facing behavior changed",
        documentation_reviewer="operator",
    )

    decision = evaluate_transition(current, LifecycleState.DONE)

    assert decision.allowed is False
    assert decision.reasons == ("documentation_reconciliation_unrecorded",)


def test_traceability_completed_reconciliation_allows_done() -> None:
    current = record(
        state=LifecycleState.DOCUMENTATION,
        traceability_required=True,
        documentation_impact=DocumentationImpact.POST_MERGE_COMPLETE,
        documentation_milestone=DocumentationMilestoneState.POST_MERGE_COMPLETE,
        documentation_event_id="doc-053-pr-63",
    )

    assert transition_record(current, LifecycleState.DONE).state is LifecycleState.DONE


def test_completion_can_require_claim_release() -> None:
    configured = load_command_plane_settings()
    configured = replace(
        configured,
        completion=replace(
            configured.completion,
            require_no_active_claim_after_close=True,
        ),
    )
    current = record(
        state=LifecycleState.DOCUMENTATION,
        execution_owner="kis-dev/session-1",
        documentation_impact=DocumentationImpact.POST_MERGE_COMPLETE,
    )

    decision = evaluate_transition(current, LifecycleState.DONE, settings=configured)

    assert decision.allowed is False
    assert decision.reasons == ("active_claim_present",)
