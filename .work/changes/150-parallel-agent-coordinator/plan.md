# Parallel Agent Coordinator Slice 3 Implementation Plan

> Execute #249 inside the existing `150-parallel-agent-coordinator` worktree. Preserve #247/#248 and do not begin #250.

**Goal:** Make coordinator mutation authority revision-safe and recoverable so stale workers cannot retain authority after scope changes, expiry, crash, or reassignment, while degraded conflict components do not block disjoint work.

**Architecture:** Extend the internal coordinator with one `AuthorityService` sharing Slice 2's canonical state root and admission mutex. Keep governed scope as repository authority through exact-claim CAS/re-read. Persist append-only revision/lease transitions, derive connected degraded components from current claims, and require exact revision/lease/fence evidence for mutation authority.

**Development level:** Complex. #249 crosses the coordinator authority boundary, mutates governed scope, introduces durable time-based lease state, and requires concurrency/restart evidence. The parent architecture and slice outcome are approved by #241/#249 and the operator assignment.

## Constraints

- Stay inside parent coordinator-owned paths.
- Preserve HR-001 / HR-002 / HR-003 exactly; do not add policy rules.
- Preserve existing #247 schemas and #248 reservation behavior unless #249 requires a compatible extension.
- Repository scope remains authoritative; coordinator journal evidence cannot silently widen it.
- Tool/runtime discovery never grants, renews, transfers, or recovers mutation authority.
- Do not implement planner/work-packet production (#250), worker execution (#251), reconciliation/integration (#252), or telemetry/commissioning (#253).
- Do not push, open a PR, merge, clean up, or restart runtimes for this slice.

### Task 1: Slice 3 concurrency and recovery contract

**Requirements:** REQ-249-01 through REQ-249-10.

- [x] Add RED tests for CAS scope amendments, stale revision/fence rejection, governed-scope re-read, lease activation/heartbeat, expiry/reassignment, restart recovery, degraded-component admission, and conflict repair.
- [x] Validate lease/scope-revision results against the existing Slice 1 schemas.

### Task 2: Authority revisions and governed scope CAS

**Requirements:** REQ-249-01, REQ-249-02, REQ-249-03, REQ-249-05, REQ-249-07.

- [x] Add validated scope-revision request handling.
- [x] Journal scope transitions before governed mutation.
- [x] Re-run global claim validation, CAS-update the target governed scope through an injected authoritative adapter, and re-read exact claim identity before accepting the next revision.
- [x] Recover interrupted scope transitions deterministically from journal plus governed-claim evidence.

### Task 3: Lease/fence lifecycle and degraded liveness

**Requirements:** REQ-249-04 through REQ-249-10.

- [x] Implement lease activation/heartbeat with an injected deterministic UTC clock.
- [x] Implement expiry recovery and explicit reassignment with monotonic revision/fence semantics.
- [x] Add an exact authority guard that rejects stale revision, lease, holder, fence, or expired evidence.
- [x] Derive connected degraded conflict components and block only intersecting new reservations.
- [x] Permit a globally valid scope amendment to reconcile an intersecting degraded component.
- [x] Harden the shared Windows admission-lock initialization path exposed by combined concurrency regression tests.

### Task 4: Documentation, review, verification, and handoff

**Requirements:** REQ-249-01 through REQ-249-10.

- [x] Update the coordinator module product spec with cumulative Slice 3 implementation status and strict #250+ boundaries.
- [x] Run focused Slice 3 + Slice 2 regression tests and the full coordinator suite.
- [x] Run affected verification, Python compilation, `git diff --check`, Ruff lint, and the governed scope check on the final implementation diff.
- [x] Perform required `code-quality`, `architecture`, and `api-contracts` reviews; automated backends required exact-diff fallback, review findings were fixed, and the final manual fallback has zero blocking findings.
- [x] Commit Slice 3 implementation on the existing parent branch and record exact handoff evidence. Leave the parent governed change active for #250.
