# Tasks: Parallel Agent Coordinator — Slice 2 (#248)

## Slice 1 prerequisite

- [x] #247 architecture/contracts committed and handed off on the existing parent branch.

## Slice 2 implementation

- [x] Confirm #248 scope and preserve strict `247 -> 248 -> 249 -> 250 -> 251 -> 252 -> 253` sequencing.
- [x] Load the canonical `develop-code` skill and re-read repository authority.
- [x] Add TDD race/admission tests and confirm the initial missing-package RED state.
- [x] Implement atomic reservation admission with a cross-process mutex.
- [x] Allocate unique human-facing sequences across active, historical, and consumed journal identities.
- [x] Reject conflicting exclusive claims and uncoordinated shared claims before authority issuance.
- [x] Preserve concurrent liveness for disjoint reservations.
- [x] Couple configured Work Management claim metadata and compensation adapters into admission.
- [x] Delegate governed branch/worktree creation to the existing change workflow and re-read the resulting claim.
- [x] Return schema-valid reservation identity with exact base, authority revision, lease ID, and initial fence token.
- [x] Enforce the declared project boundary for coordinator durable state.

## Remaining Slice 2 gates

- [x] Update long-lived module documentation for implemented Slice 2 behavior.
- [x] Full coordinator and affected regression verification passes on the final diff.
- [x] Required code-quality, architecture, and API-contract reviews have zero blocking findings after documented fallback/adjudication.
- [x] Governed scope check, compilation, and `git diff --check` pass.
- [ ] Commit Slice 2 and record exact handoff evidence.

## Explicitly deferred

- #249 CAS scope mutation, lease enforcement, fencing lifecycle, expiry/reassignment, and recovery.
- #250 dependency planning, work-packet production, runtime resolution, and agent selection.
- #251 durable worker execution/retry/resume and MCP adapter behavior.
- #252 handoff reconciliation, verification derivation, serialized integration, and landing.
- #253 observability, evaluation, operator UX, Control Center integration, and commissioning.
