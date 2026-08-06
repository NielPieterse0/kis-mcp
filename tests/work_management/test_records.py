from __future__ import annotations

import pytest

from kis_mcp.work_management import LifecycleState, RecordType, WorkRecord
from kis_mcp.work_management.records import (
    ApprovalDetails,
    AssumptionDetails,
    DecisionDetails,
    GovernanceRecord,
    HoldDetails,
    RiskDetails,
)


def record(record_type: RecordType, record_id: str) -> WorkRecord:
    return WorkRecord(
        record_id=record_id,
        project_id="kis-mcp",
        title="Example",
        record_type=record_type,
    )


def test_decision_requires_authority_and_consequences() -> None:
    details = DecisionDetails(
        decision="Use provider-neutral contracts",
        owner="operator",
        authority_paths=("SPEC.md",),
        alternatives=("Provider-specific domain",),
        consequences=("Adapters own transport details",),
    )
    value = GovernanceRecord(record(RecordType.DECISION, "DEC-1"), details)

    assert value.record.state is LifecycleState.INBOX
    assert value.to_json_dict()["details"]["authority_paths"] == ["SPEC.md"]


def test_assumption_requires_validation_and_trigger() -> None:
    value = GovernanceRecord(
        record(RecordType.ASSUMPTION, "ASM-2"),
        AssumptionDetails(
            statement="Project fields remain available",
            confidence="medium",
            validation_method="Inventory the configured Project",
            review_trigger="Before enabling mutation",
            invalidation_condition="Required field is absent",
        ),
    )

    assert value.to_json_dict()["details"]["confidence"] == "medium"


def test_risk_and_approval_are_first_class_records() -> None:
    risk = GovernanceRecord(
        record(RecordType.RISK, "RISK-3"),
        RiskDetails(
            statement="Concurrent edits may conflict",
            likelihood="possible",
            consequence="Operator changes could be overwritten",
            mitigation="Use optimistic concurrency",
        ),
    )
    approval = GovernanceRecord(
        record(RecordType.APPROVAL, "APP-4"),
        ApprovalDetails(
            decision="Approve Project mutation",
            approver="operator",
            scope="Configured project only",
        ),
    )

    assert risk.record.record_type is RecordType.RISK
    assert approval.record.record_type is RecordType.APPROVAL


def test_hold_requires_review_trigger_and_protected_assets() -> None:
    with pytest.raises(ValueError, match="review_trigger"):
        HoldDetails(
            reason="Dependency incomplete",
            owner="operator",
            protected_assets=(".work/worktrees/040-context7-serena-adapters",),
            review_trigger="",
            resumption_conditions="Dependency completed",
            cancellation_conditions="Operator cancels",
        )

    value = GovernanceRecord(
        record(RecordType.HOLD, "HOLD-5"),
        HoldDetails(
            reason="Dependency incomplete",
            owner="operator",
            protected_assets=(".work/worktrees/040-context7-serena-adapters",),
            review_trigger="After modularity work",
            resumption_conditions="Dependency completed",
            cancellation_conditions="Operator cancels",
        ),
    )
    assert value.to_json_dict()["details"]["protected_assets"] == [
        ".work/worktrees/040-context7-serena-adapters"
    ]


def test_record_type_discriminator_cannot_be_overridden() -> None:
    with pytest.raises(TypeError):
        DecisionDetails(
            decision="Invalid discriminator",
            owner="operator",
            authority_paths=("SPEC.md",),
            consequences=("Reject construction",),
            record_type=RecordType.RISK,
        )


def test_governance_details_must_match_record_type() -> None:
    with pytest.raises(ValueError, match="must match"):
        GovernanceRecord(
            record(RecordType.DECISION, "DEC-6"),
            RiskDetails(
                statement="Mismatch",
                likelihood="possible",
                consequence="Invalid record",
                mitigation="Reject it",
            ),
        )
