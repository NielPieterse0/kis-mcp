# Change Specification: Deterministic Housekeeping

- **Change ID**: `194-deterministic-housekeeping`
- **Status**: Active
- **Complexity**: medium
- **Risk trigger**: `external_action`

## Outcome

Reimplement the still-valid deterministic housekeeping foundation from historical Change 176 / PR #327 as fresh code against current Work Management and GitHub provider contracts.

## Authority and scope

- Authorities: `AGENTS.md`, current Work Management command-plane settings/contracts, current GitHub provider schema, issue #364, and this change record.
- Historical PR #327 is implementation evidence only; no cherry-pick or merge replay is permitted.
- Owned: `src/kis_mcp/housekeeping/**`, `tests/housekeeping/**`, `scripts/housekeeping.py`, this change record.
- Excluded: `src/kis_mcp/execution/**`, `.github/workflows/**`.
- Dependency: Change 193 / issue #363 is complete; Change 194 starts from verified `main` `cea1858252b1dbda88304dd6a0346d1107a799b7`.

## Requirements

- **REQ-001**: Provide typed manual/scheduled triggers; preview is default and apply requires an idempotency key.
- **REQ-002**: Reconciliation fails closed on truncated or incomplete source evidence and never guesses lifecycle intent.
- **REQ-003**: Missing Project records may be proposed only from one unique governed source binding whose GitHub source is open.
- **REQ-004**: Report lifecycle, stale-claim, readiness-metadata, and Change-ID projection drift without directly overriding evidence-owned fields.
- **REQ-005**: Backlog readiness reuses `project_management_next_work`; only open, unclaimed work is eligible for a `ready` proposal, and the existing transition gate must also accept it.
- **REQ-006**: Only exact dependency references are resolved mechanically; semantic dependency text is a conflict with no mutation path.
- **REQ-007**: Receipts are bounded, deterministic, provider-neutral, and contain no LLM decision or mutation authority.

## Acceptance

1. Truncated Project inventory yields `complete=false`, a typed conflict, and zero applied actions.
2. Unique open governed work absent from the Project yields an exact capture proposal; apply uses a derived idempotency key.
3. Closed source work that remains operationally active/claimed and mismatched Change-ID projection is reported without guessing a terminal correction.
4. Blocked work with no dependency evidence is proposed for Ready only when its source issue is open, it has no execution claim, and the existing Work Management gate accepts it.
5. Exact closed dependencies and ambiguous dependency text are reported deterministically without clearing evidence-owned dependency fields.
6. The CLI invokes both runners through the same provider-neutral state machine.
7. Focused tests, scope/governance checks, required reviews, and canonical GitHub Actions pass on one frozen exact PR head before merge.

## Risks and recovery

- Risk: stale or incomplete provider evidence could otherwise drive an unsafe Project mutation.
- Mitigation: bounded reads, preview-first planning, revision-aware existing gates, idempotency, and fail-closed completeness checks.
- Recovery: rerun with the same idempotency key; no destructive repository or execution-provider operation is introduced.

## Out of scope

- Scheduler/execution-provider implementation, Actions workflow changes, automatic semantic dependency inference, and restoration of obsolete local/VM execution architecture.
