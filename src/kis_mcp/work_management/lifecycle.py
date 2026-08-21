from __future__ import annotations

from dataclasses import dataclass, replace

from .canonical_contracts import load_canonical_work_contracts
from .command_settings import CommandPlaneSettings, load_command_plane_settings
from .contracts import (
    DocumentationImpact,
    DocumentationMilestoneState,
    DocumentationMode,
    LifecycleState,
    WorkRecord,
)


@dataclass(frozen=True, slots=True)
class TransitionDecision:
    allowed: bool
    source: LifecycleState
    target: LifecycleState
    reasons: tuple[str, ...] = ()


class TransitionRejected(ValueError):
    def __init__(self, decision: TransitionDecision) -> None:
        self.decision = decision
        reasons = ", ".join(decision.reasons) or "transition_rejected"
        super().__init__(reasons)


def _documentation_complete(record: WorkRecord) -> bool:
    if record.documentation_impact is DocumentationImpact.POST_MERGE_COMPLETE:
        return True
    return (
        record.documentation_impact is DocumentationImpact.NONE
        and record.documentation_rationale is not None
        and record.documentation_reviewer is not None
    )


def _guard_applies(condition: str, record: WorkRecord, configured: CommandPlaneSettings) -> bool:
    if condition == "approval_required_and_incomplete":
        return record.approval_required and not record.approval_complete
    if condition == "completion_requires_no_active_claim_and_claim_present":
        return configured.completion.require_no_active_claim_after_close and record.execution_owner is not None
    if condition == "required_documentation_reconciliation_due":
        return (
            record.traceability_required
            and record.documentation_milestone is DocumentationMilestoneState.DOCUMENTATION_RECONCILIATION_DUE
            and record.documentation_mode is DocumentationMode.REQUIRED
        )
    if condition == "advisory_documentation_reconciliation_due":
        return (
            record.traceability_required
            and record.documentation_milestone is DocumentationMilestoneState.DOCUMENTATION_RECONCILIATION_DUE
            and record.documentation_mode is DocumentationMode.ADVISORY
        )
    if condition == "required_documentation_reconciliation_unrecorded":
        return (
            record.traceability_required
            and record.documentation_mode is DocumentationMode.REQUIRED
            and record.documentation_milestone is not DocumentationMilestoneState.POST_MERGE_COMPLETE
        )
    if condition == "advisory_documentation_reconciliation_unrecorded":
        return (
            record.traceability_required
            and record.documentation_mode is DocumentationMode.ADVISORY
            and record.documentation_milestone is not DocumentationMilestoneState.POST_MERGE_COMPLETE
        )
    if condition == "required_documentation_incomplete":
        return record.documentation_mode is DocumentationMode.REQUIRED and not _documentation_complete(record)
    if condition == "advisory_documentation_incomplete":
        return record.documentation_mode is DocumentationMode.ADVISORY and not _documentation_complete(record)
    raise ValueError(f"unsupported canonical lifecycle guard condition: {condition}")


def evaluate_transition(
    record: WorkRecord,
    target: LifecycleState,
    *,
    settings: CommandPlaneSettings | None = None,
) -> TransitionDecision:
    if not isinstance(record, WorkRecord):
        raise ValueError("record must be a WorkRecord")
    if not isinstance(target, LifecycleState):
        raise ValueError("target must be a LifecycleState value")
    configured = settings or load_command_plane_settings()

    if target not in configured.transition_targets(record.state):
        return TransitionDecision(
            allowed=False,
            source=record.state,
            target=target,
            reasons=("transition_not_declared",),
        )

    canonical = load_canonical_work_contracts().lifecycle
    for guard in canonical.guards:
        if guard.target != target.value:
            continue
        if not _guard_applies(guard.condition, record, configured):
            continue
        return TransitionDecision(
            allowed=guard.disposition == "allow_with_reason",
            source=record.state,
            target=target,
            reasons=(guard.reason_code,),
        )

    return TransitionDecision(allowed=True, source=record.state, target=target)


def transition_record(
    record: WorkRecord,
    target: LifecycleState,
    *,
    settings: CommandPlaneSettings | None = None,
) -> WorkRecord:
    decision = evaluate_transition(record, target, settings=settings)
    if not decision.allowed:
        raise TransitionRejected(decision)
    return replace(record, state=target)


__all__ = [
    "TransitionDecision",
    "TransitionRejected",
    "evaluate_transition",
    "transition_record",
]
