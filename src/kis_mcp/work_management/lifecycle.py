from __future__ import annotations

from dataclasses import dataclass, replace

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

    if (
        target is LifecycleState.ACTIVE
        and record.approval_required
        and not record.approval_complete
    ):
        return TransitionDecision(
            allowed=False,
            source=record.state,
            target=target,
            reasons=("approval_incomplete",),
        )

    if (
        target is LifecycleState.DONE
        and configured.completion.require_no_active_claim_after_close
        and record.execution_owner is not None
    ):
        return TransitionDecision(
            allowed=False,
            source=record.state,
            target=target,
            reasons=("active_claim_present",),
        )

    if target is LifecycleState.DONE and record.traceability_required:
        if (
            record.documentation_milestone
            is DocumentationMilestoneState.DOCUMENTATION_RECONCILIATION_DUE
        ):
            if record.documentation_mode is DocumentationMode.REQUIRED:
                return TransitionDecision(
                    allowed=False,
                    source=record.state,
                    target=target,
                    reasons=("documentation_reconciliation_due",),
                )
            if record.documentation_mode is DocumentationMode.ADVISORY:
                return TransitionDecision(
                    allowed=True,
                    source=record.state,
                    target=target,
                    reasons=("documentation_reconciliation_advisory_due",),
                )
        if (
            record.documentation_mode is DocumentationMode.REQUIRED
            and record.documentation_milestone
            is not DocumentationMilestoneState.POST_MERGE_COMPLETE
        ):
            return TransitionDecision(
                allowed=False,
                source=record.state,
                target=target,
                reasons=("documentation_reconciliation_unrecorded",),
            )
        if (
            record.documentation_mode is DocumentationMode.ADVISORY
            and record.documentation_milestone
            is not DocumentationMilestoneState.POST_MERGE_COMPLETE
        ):
            return TransitionDecision(
                allowed=True,
                source=record.state,
                target=target,
                reasons=("documentation_reconciliation_advisory_incomplete",),
            )

    if target is LifecycleState.DONE:
        if (
            record.documentation_mode is DocumentationMode.REQUIRED
            and not _documentation_complete(record)
        ):
            return TransitionDecision(
                allowed=False,
                source=record.state,
                target=target,
                reasons=("documentation_incomplete",),
            )
        if (
            record.documentation_mode is DocumentationMode.ADVISORY
            and not _documentation_complete(record)
        ):
            return TransitionDecision(
                allowed=True,
                source=record.state,
                target=target,
                reasons=("documentation_advisory_incomplete",),
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
