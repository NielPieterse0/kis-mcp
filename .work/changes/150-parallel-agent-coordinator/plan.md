# Parallel Agent Coordinator Slice 5 Implementation Plan

> Execute #251 inside existing `150-parallel-agent-coordinator`. Consume landed #278 for durable state placement; do not invent ownership/namespace semantics.

**Goal:** Complete deterministic worker lifecycle semantics, the ephemeral MCP worker adapter, and restart-safe durable execution persistence without weakening #248/#249 mutation authority.

**Architecture:** Keep three layers distinct. `WorkerExecution` models location-independent lifecycle and correlation facts. `McpWorkerAdapter` owns process-local connection/discovery/filter/invoke/reconnect behavior and requires injected authority/tool-policy checks. `WorkerExecutionStore` persists only execution/effect evidence beneath the exact #278 `DURABLE_EVIDENCE` namespace resolved from project identity plus `derive_change_source_id(change_id)`; live MCP objects remain ephemeral and non-authorizing.

**Development level:** Complex. #251 crosses public contracts, mutation-authority enforcement, MCP transport, retry/idempotence, and persistent-state recovery.

## Constraints

- Stay inside parent coordinator-owned paths.
- Preserve HR-001 / HR-002 / HR-003 exactly.
- Preserve #248/#249 reservation, lease, revision, and fence semantics as the only mutation authority.
- MCP/runtime discovery remains advisory and non-authorizing.
- Durable state ownership/location comes only from landed #278 APIs.
- Do not implement #252 or #253 behavior.
- Do not merge without canonical provider-native exact-head GitHub Actions evidence.

### Task 1: Slice 5 contracts and RED tests

**Requirements:** REQ-251-01 through REQ-251-10.

- [x] Add RED tests for lifecycle transitions, idempotent duplicate/stale events, correlation IDs, tool filtering, authority re-check, reconnect non-authority, and structured result facts.
- [x] Add/revise strict coordinator schemas needed for Slice 5 execution and handoff correlation.
- [x] Lock the #278 dependency boundary so no implicit local persistence root is introduced.

### Task 2: Location-independent execution lifecycle

**Requirements:** REQ-251-01 through REQ-251-03, REQ-251-07.

- [x] Implement immutable execution identity/record models and deterministic legal transition rules.
- [x] Make exact duplicate events idempotent and conflicting/stale attempts typed failures.
- [x] Produce structured completion/failure/cancellation facts without consuming assignment keys or reconciling handoffs.

### Task 3: Ephemeral MCP worker adapter

**Requirements:** REQ-251-04 through REQ-251-07, REQ-251-09.

- [x] Implement injected async MCP transport lifecycle: connect, discover, filter, invoke, progress/result normalization, cleanup, reconnect.
- [x] Enforce filtered tool names at both discovery and invocation boundaries.
- [x] Re-check current Slice 3 authority before mutating invocation; transport reconnect alone never calls an authority mutation.

### Task 4: #278 persistence integration

**Requirements:** REQ-251-08, REQ-251-09.

- [x] Re-read landed #278 and consume `StateOwnershipClass.DURABLE_EVIDENCE`, `StateNamespaceResolver`, `StateNamespaceRequest`, and `derive_change_source_id` directly.
- [x] Implement the durable execution journal/store only beneath the #278-resolved durable-evidence namespace.
- [x] Restore ordered execution history after restart and preserve idempotent resume/retry behavior.
- [x] Persist mutation receipts before dispatch so completed retries return the prior result and uncertain in-flight work fails closed instead of executing twice.
- [x] Bind durable mutation evidence and structured results to execution, attempt, reservation/revision/lease/fence, runtime binding, arguments, progress, and result identity.

### Task 5: Documentation, review, verification, and handoff

- [x] Update the coordinator product spec with only actually implemented Slice 5 behavior.
- [x] Run focused Slice 5 tests, full coordinator regression tests, compilation, Ruff, governed change check, and `git diff --check` on the final implementation diff.
- [x] Run required code-quality, architecture, API-contract, and persistence/recovery review gates; resolve actionable #251 findings and document evidence-disproved compatibility concerns.
- [x] Resolve blocking #251-scoped findings in corrective commit `7423a83` and rerun focused/full local verification.
- [x] Prepare the final documentation/review evidence for freeze; after committing, rerun exact-head local checks and queue the frozen head for canonical GitHub Actions verification/merge once the disposable Windows runner is available; do not merge beforehand.
