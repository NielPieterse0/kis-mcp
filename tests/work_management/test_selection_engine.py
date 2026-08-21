from __future__ import annotations

from kis_mcp.work_management.selection import (
    SelectionFacts,
    evaluate_selection_facts,
    selection_rank_key,
)


def facts(**overrides: object) -> SelectionFacts:
    values: dict[str, object] = {
        "candidate_id": "candidate-1",
        "project_id": "alpha-project",
        "state": "ready",
        "priority": "medium",
        "effort": "medium",
        "created_order": 5,
        "stable_id": "alpha#1",
    }
    values.update(overrides)
    return SelectionFacts(**values)  # type: ignore[arg-type]


def test_provider_profile_preserves_existing_reason_order() -> None:
    result = evaluate_selection_facts(
        facts(
            source_issue=False,
            source_open=False,
            state="active",
            priority=None,
            effort=None,
            required_fields_missing=("Record Type",),
            claimed_owner="agent-1",
            dependency_evidence_required=True,
            dependency_evidence_available=False,
            dependency_blockers=("#9",),
        ),
        profile="provider_project",
    )

    assert result.eligible is False
    assert result.reasons == (
        "not_issue",
        "source_not_open",
        "state_not_ready",
        "missing_or_invalid:Priority",
        "missing_or_invalid:Effort",
        "missing_required:Record Type",
        "already_claimed:agent-1",
        "dependency_evidence_unavailable",
        "native_dependency_blocking",
    )
    assert result.rule_ids == (
        "SEL-001", "SEL-002", "SEL-004", "SEL-005", "SEL-006",
        "SEL-007", "SEL-008", "SEL-010", "SEL-011",
    )


def test_domain_profile_preserves_dependency_specific_reasons() -> None:
    result = evaluate_selection_facts(
        facts(
            project_match=False,
            state="on_hold",
            claimed_owner="agent-2",
            approval_required=True,
            approval_complete=False,
            dependency_blockers=("TASK-9", "TASK-10"),
        ),
        profile="normalized_domain",
    )

    assert result.reasons == (
        "project_mismatch",
        "state_not_executable",
        "already_claimed:agent-2",
        "approval_incomplete",
        "dependency_incomplete:TASK-9",
        "dependency_incomplete:TASK-10",
    )


def test_shared_rank_key_is_priority_effort_age_then_stable_identity() -> None:
    critical_large = facts(priority="critical", effort="large", created_order=1, stable_id="z")
    critical_tiny_new = facts(priority="critical", effort="tiny", created_order=8, stable_id="b")
    critical_tiny_old = facts(priority="critical", effort="tiny", created_order=3, stable_id="c")
    high_tiny = facts(priority="high", effort="tiny", created_order=0, stable_id="a")

    ordered = sorted(
        (critical_large, critical_tiny_new, critical_tiny_old, high_tiny),
        key=selection_rank_key,
    )
    assert ordered == [critical_tiny_old, critical_tiny_new, critical_large, high_tiny]
