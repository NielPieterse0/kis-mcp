# Change Specification: Mutation Budget Forward Progress

- **Change ID**: `632-mutation-budget-forward-progress`
- **Status**: Active
- **Risk Profile**: standard; `external_action`, `persistent_state`

## Outcome

Process newer commissioning candidates first so fresh governed merges are evaluated before historical backlog can exhaust the shared scan-wide mutation budget.

## Requirements

- **REQ-001**: Candidate processing order is deterministic newest-first by pull request number within the bounded search window.
- **REQ-002**: The shared `max_mutations` ceiling remains scan-wide and fail-closed; exhaustion still fails the scan.
- **REQ-003**: Per-candidate external-read isolation from #641 remains unchanged.
- **REQ-004**: Checkpoint preservation and exact merge/change identity semantics remain unchanged.

## Acceptance

1. Multi-candidate runtime tests prove newest-first processing.
2. Mutation-budget exhaustion still returns whole-scan `CommissioningBudgetError` and preserves the checkpoint.
3. Focused and full post-merge commissioning tests, governance checks, review, and exact-head CI pass.

## Out of scope

Increasing mutation authority, rewriting checkpoints, or making mutation exhaustion candidate-local.