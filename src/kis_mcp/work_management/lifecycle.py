from __future__ import annotations

from dataclasses import dataclass, replace

from .contracts import (
    DocumentationImpact,
    DocumentationMode,
    LifecycleState,
    WorkRecord,
)

_SUPERSEDABLE_STATES = frozenset(
    {
        LifecycleState.INBOX,
        LifecycleState.TRIAGE,
        LifecycleState.PROPOSED,
        LifecycleState.APPROVED,
        LifecycleState.ACTIVE,
        LifecycleState.REVIEW,
        LifecycleState.VERIFICATION,
        LifecycleState.DOCUMENTATION,
        LifecycleState.BLOCKED,
        LifecycleState.ON_HOLD,
        LifecycleState.DEFERRED,
    }
)

_ALLOWED_TRANSITIONS: dict[LifecycleState, frozenset[LifecycleState]] = {
    LifecycleState.INBOX: frozenset(
        {LifecycleState.TRIAGE, LifecycleState.DEFERRED, LifecycleState.REJECTED}
    ),
    LifecycleState.TRIAGE: frozenset(
        {
            LifecycleState.PROPOSED,
            LifecycleState.APPROVED,
            LifecycleState.DEFERRED,
            LifecycleState.REJECTED,
        }
    ),
    LifecycleState.PROPOSED: frozenset(
        {LifecycleState.APPROVED, LifecycleState.DEFERRED, LifecycleState.REJECTED}
    ),
    LifecycleState.APPROVED: frozenset(
        {LifecycleState.ACTIVE, LifecycleState.ON_HOLD, LifecycleState.DEFERRED}
    ),
    LifecycleState.ACTIVE: frozenset(
        {
            LifecycleState.REVIEW,
            LifecycleState.BLOCKED,
            LifecycleState.ON_HOLD,
            LifecycleState.DEFERRED,
        }
    ),
    LifecycleState.REVIEW: frozenset(
        {
            LifecycleState.ACTIVE,
            LifecycleState.VERIFICATION,
            LifecycleState.BLOCKED,
            LifecycleState.ON_HOLD,
        }
    ),
    LifecycleState.VERIFICATION: frozenset(
        {
            LifecycleState.ACTIVE,
            LifecycleState.DOCUMENTATION,
            LifecycleState.BLOCKED,
        }
    ),
    LifecycleState.DOCUMENTATION: frozenset(
        {LifecycleState.DONE, LifecycleState.ACTIVE, LifecycleState.BLOCKED}
    ),
    LifecycleState.BLOCKED: frozenset(
        {LifecycleState.ACTIVE, LifecycleState.ON_HOLD, LifecycleState.DEFERRED}
    ),
    LifecycleState.ON_HOLD: frozenset(
        {LifecycleState.ACTIVE, LifecycleState.DEFERRED, LifecycleState.REJECTED}
    ),
    LifecycleState.DEFERRED: frozenset(
        {LifecycleState.TRIAGE, LifecycleState.PROPOSED, LifecycleState.REJECTED}
    ),
    LifecycleState.REJECTED: frozenset({LifecycleState.TRIAGE}),
    LifecycleState.DONE: frozenset(),
    LifecycleState.SUPERSEDED: frozenset(),
}


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
) -> TransitionDecision:
    if not isinstance(record, WorkRecord):
        raise ValueError("record must be a WorkRecord")
    if not isinstance(target, LifecycleState):
        raise ValueError("target must be a LifecycleState value")

    if target is LifecycleState.SUPERSEDED and record.state in _SUPERSEDABLE_STATES:
        return TransitionDecision(
            allowed=True,
            source=record.state,
            target=target,
        )

    if target not in _ALLOWED_TRANSITIONS[record.state]:
        return TransitionDecision(
            allowed=False,
            source=record.state,
            target=target,
            reasons=("transition_not_declared",),
        )

    if target is LifecycleState.ACTIVE:
        if record.approval_required and not record.approval_complete:
            return TransitionDecision(
                allowed=False,
                source=record.state,
                target=target,
                reasons=("approval_incomplete",),
            )

    if target is LifecycleState.DONE:
        if record.documentation_mode is DocumentationMode.REQUIRED:
            if not _documentation_complete(record):
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

    return TransitionDecision(
        allowed=True,
        source=record.state,
        target=target,
    )


def transition_record(record: WorkRecord, target: LifecycleState) -> WorkRecord:
    decision = evaluate_transition(record, target)
    if not decision.allowed:
        raise TransitionRejected(decision)
    return replace(record, state=target)


__all__ = [
    "TransitionDecision",
    "TransitionRejected",
    "evaluate_transition",
    "transition_record",
]
