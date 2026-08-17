# Parallel Agent Coordinator Slice 6 Implementation Plan

> Execute #252 inside existing `150-parallel-agent-coordinator` after verified Slice 5 landing.

**Goal:** Make worker handback mechanically reviewable-or-rejected, derive exact verification gates from repository authority, and serialize integration/landing ownership.

**Architecture:** Add one internal `reconciliation` module. `ReconciliationService` validates worker handoff against durable packet assignment, current reservation/fence/global claims, independent Git observation, dependency state, and local scope. `VerificationRequirementService` derives checks/reviews from changed paths plus configured change controls. `IntegrationQueueService` serializes accepted candidates and requires referenced KIS-local exact-head verification before delivery authorization.

**Development level:** Complex. #252 crosses authority consumption, persistent state, public contracts, global claim safety, verification policy, and integration serialization.

## Constraints

- Stay inside parent coordinator-owned paths.
- Preserve HR-001 / HR-002 / HR-003 exactly.
- Preserve #248/#249 authority and #251 durable worker semantics.
- Use repository change-control settings for risk-to-review mapping; do not duplicate that policy.
- Canonical landing verification is KIS-local exact-head evidence after change 179; GitHub Actions is diagnostic only.
- Actual GitHub mutation remains in existing registered KIS operations.
- Do not implement #253 telemetry/Control Center/commissioning.

### Task 1: Slice 6 RED tests and contract correction

**Requirements:** REQ-252-01 through REQ-252-10.

- [x] Add RED tests for stale/mismatched handoffs, independent Git evidence, local scope/global claim validation, dependency blocking, assignment consumption, and duplicate handback.
- [x] Add RED tests for deterministic verification derivation and configured risk-review mapping.
- [x] Version verification requirements away from stale provider-native-CI semantics to `kis_local_exact_head` authority.
### Task 2: Deterministic reconciliation

- [x] Implement strict identity/status/dependency validation against packet + handoff + observed Git evidence.
- [x] Re-read current reservation authority and current governed claim graph before acceptance and accepted replay.
- [x] Reject changed paths outside packet scope.
- [x] Atomically consume the active assignment key only for an accepted handoff; preserve idempotent replay of the same accepted reconciliation.

### Task 3: Verification requirements

- [x] Derive deterministic check categories from changed paths and caller-supplied repository verification IDs.
- [x] Reuse `select_change_controls` for configured base/risk review requirements.
- [x] Emit strict v2 verification requirements with exact-head local KIS authority.

### Task 4: Serialized integration

- [x] Persist one queue record per accepted reconciliation and serialize queue mutation with a cross-process lock.
- [x] Enforce one active integration owner/candidate at a time per integration key.
- [x] Require passing referenced `local` verification matching the exact candidate head before delivery authorization.
- [x] Keep repository delivery distinct from commissioning/closeout.

### Task 5: Documentation, review, verification, landing

- [x] Update the coordinator module product spec to implemented Slice 6 behavior and change-179 landing semantics.
- [x] Run focused Slice 6 tests, full coordinator regressions, Ruff/compile, change-governance check, and `git diff --check`.
- [x] Run configured code-quality, architecture, and API-contract reviews plus persistent-state/trust-boundary fallback review; resolve blocking findings.
- [x] Reconcile the exact candidate, run canonical local exact-head verification, and land only that head to local `main`; GitHub PR synchronization is retained as remote-mirror debt after repeated HTTP 503 failures. #253 begins only after this Slice 6 closeout is recorded.
