# Tasks: Parallel Agent Coordinator — Slice 3 (#249)

## Prerequisites

- [x] #247 architecture/contracts completed and preserved.
- [x] #248 atomic reservation admission completed and preserved.
- [x] Parent branch reconciled onto verified current `main` `7d4391873b17064fcb1ce32c1dc3915a4b6a0cf4` with no coordinator-path conflicts.
- [x] Repository authority and #241/#249 re-read; canonical `develop-code` and `develop-docs` procedures loaded.
- [x] Strict `247 -> 248 -> 249 -> 250 -> 251 -> 252 -> 253` sequencing preserved.

## Slice 3 implementation

- [x] Add test-first CAS scope-revision concurrency coverage.
- [x] Keep governed scope authoritative through exact observed-claim CAS and post-write re-read.
- [x] Persist revision/lease/recovery transitions append-only.
- [x] Implement lease activation and heartbeat with exact holder/revision/lease/fence checks.
- [x] Implement expiry recovery and reassignment with monotonic authority revision/fence semantics.
- [x] Reject stale mutation authority after scope revision, expiry, or reassignment.
- [x] Derive stable connected degraded path-conflict components from current claims.
- [x] Reject reservations intersecting degraded components while preserving disjoint admission.
- [x] Permit valid scope repair that removes a degraded conflict.
- [x] Preserve Slice 1/2 reservation behavior and harden the Windows admission-lock initialization race found by combined regression testing.
- [x] Keep Slice 3 internal; add no planner, work packet, worker, reconciliation, telemetry, or public coordinator tool.

## Slice 3 gates

- [x] Affected change-governance + full coordinator regression suite passes: 83/83.
- [x] Lease and scope-revision outputs validate against existing Slice 1 contracts.
- [x] Coordinator module documentation reconciled to implemented Slice 3 behavior.
- [x] Ruff lint, Python compilation, governed scope check, and `git diff --check` pass on the final implementation diff.
- [x] Required code-quality, architecture, and API-contract reviews have zero blocking findings after exact-diff fallback fixes/adjudication.
- [x] Slice 3 implementation commit `530d18f4c7ae181cca0bdef6f879952bef8574d0` recorded; parent change remains active for #250.

## Explicitly deferred

- #250 dependency planning, work-packet production, assignment keys, runtime/capability resolution, and agent selection.
- #251 durable worker execution/retry/resume and MCP adapter behavior.
- #252 handoff reconciliation, verification derivation, serialized integration, and landing.
- #253 observability, evaluation, operator UX, Control Center integration, and commissioning.
