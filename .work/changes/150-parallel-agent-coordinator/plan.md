# Parallel Agent Coordinator Slice 5 Implementation Plan

> Execute #251 inside existing `150-parallel-agent-coordinator`. Consume #278 for new durable state placement; do not invent ownership/namespace semantics.

**Goal:** Add deterministic worker lifecycle semantics and an ephemeral MCP worker adapter, then bind restart-safe persistence to #278 when its contract becomes available.

**Architecture:** Keep three layers distinct. `WorkerExecution` models location-independent lifecycle and correlation facts. `McpWorkerAdapter` owns process-local connection/discovery/filter/invoke/reconnect behavior and requires injected authority/tool-policy checks. Durable storage is a separate adapter whose namespace must be supplied by #278; no path resolver is implemented in this slice before that dependency exists.

**Development level:** Complex. #251 crosses public contracts, mutation-authority enforcement, MCP transport, retry/idempotence, and persistent-state recovery. The user assignment plus #241/#251/#278 establish the approved architecture and dependency boundary.

## Constraints

- Stay inside parent coordinator-owned paths.
- Preserve HR-001 / HR-002 / HR-003 exactly.
- Preserve #248/#249 reservation, lease, revision, and fence semantics as the only mutation authority.
- MCP/runtime discovery remains advisory and non-authorizing.
- New durable state location/ownership MUST come from #278.
- Do not implement #252 or #253 behavior.
- Do not push, open/merge a PR, clean up, or restart runtimes unless separately assigned.

### Task 1: Slice 5 contracts and RED tests

**Requirements:** REQ-251-01 through REQ-251-10.

- [ ] Add RED tests for lifecycle transitions, idempotent duplicate/stale events, correlation IDs, tool filtering, authority re-check, reconnect non-authority, and structured result facts.
- [ ] Add/revise strict coordinator schemas needed for Slice 5 execution and handoff correlation.
- [ ] Lock the #278 dependency with a test/contract boundary that forbids an implicit local persistence root.

### Task 2: Location-independent execution lifecycle

**Requirements:** REQ-251-01 through REQ-251-03, REQ-251-07.

- [ ] Implement immutable execution identity/record models and deterministic legal transition rules.
- [ ] Make exact duplicate events idempotent and conflicting/stale attempts typed failures.
- [ ] Produce structured completion/failure/cancellation facts without consuming assignment keys or reconciling handoffs.

### Task 3: Ephemeral MCP worker adapter

**Requirements:** REQ-251-04 through REQ-251-07, REQ-251-09.

- [ ] Implement injected async MCP transport lifecycle: connect, discover, filter, invoke, progress/result normalization, cleanup, reconnect.
- [ ] Enforce filtered tool names at both discovery and invocation boundaries.
- [ ] Re-check current Slice 3 authority before mutating invocation; transport reconnect alone never calls an authority mutation.

### Task 4: #278 persistence integration

**Requirements:** REQ-251-08, REQ-251-09.

- [ ] Re-read #278 implementation once available and consume its exact ownership enum/resolver API.
- [ ] Implement durable execution journal/store only beneath the #278-resolved durable-evidence namespace.
- [ ] Add restart/recovery and idempotent resume/retry tests proving completed mutation work is not duplicated.
- [ ] STOP at this task while #278 is unavailable; do not substitute the prior caller-supplied `state_root` convention.

### Task 5: Documentation, review, verification, and handoff

- [ ] Update the coordinator product spec with only actually implemented Slice 5 behavior and explicit residual dependency.
- [ ] Run focused Slice 5 tests, full coordinator regression tests, compilation, Ruff, scope check, and `git diff --check`.
- [ ] Run required code-quality, architecture, API-contract, and persistence/recovery review gates on the current diff.
- [ ] Commit only verified #251 work. Keep #251 open if Task 4 remains dependency-blocked.
