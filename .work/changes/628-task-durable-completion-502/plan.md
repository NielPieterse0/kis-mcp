# Task Durable Completion 502 Implementation Plan

**Goal:** Eliminate accidental long synchronous completion calls that can surface gateway 502s after external work has already progressed.

**Architecture:** Keep the existing completion coordinator and registered GitHub reconciliation authority unchanged. Change only the MCP transport contract: the normal completion tool requires Tasks; a separately named compatibility tool remains synchronous. Reuse the same service function for both surfaces.

**Tech Stack:** Python 3.11, FastMCP 4 / `fastmcp[tasks]`, pytest, KIS governed change workflow.

## Global constraints

- Stay inside `scope.json` and preserve exact-head/default identity checks.
- MCP Tasks do not become Work or mutation authority.
- Do not introduce duplicate publication/PR operations or a second completion state machine.

### Task 1: Transport contract

- [x] Add required-task and synchronous-fallback task configurations.
- [x] Make `prepare_reviewable_pull_request` task-required.
- [x] Add explicit `prepare_reviewable_pull_request_sync` compatibility surface using the same coordinator.

### Task 2: Regression evidence

- [x] Prove completion task creation/reconnect returns the terminal result.
- [x] Prove reconnect does not execute completion twice.
- [x] Preserve existing response-loss reconciliation tests.

### Task 3: Documentation and closeout

- [x] Update current `SPEC.md` task-boundary truth.
- [ ] Run scope check and focused verification.
- [ ] Complete independent code/test/API-contract review.
- [ ] Publish, pass exact-head Actions, merge, and use the merge as #641 fresh observer acceptance evidence.
