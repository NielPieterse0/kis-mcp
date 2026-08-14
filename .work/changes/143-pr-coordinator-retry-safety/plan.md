# PR Coordinator Retry Safety Implementation Plan

**Goal:** Make exact registered PR preparation retry-safe across publication and PR-creation partial success without weakening authority checks.

**Architecture:** Reconstruct prior exact external state instead of persisting a second coordinator database. The registered publication primitive recognizes only a branch with the expected reconciled tree, sole remote-default parent, and source-bound message. The PR primitive searches bounded PR history and reuses only one exact open non-draft PR; terminal/conflicting history fails closed. The coordinator exposes typed retry diagnostics.

**Tech Stack:** Python, pytest, Git/gh registered operations, FastMCP.

## Global constraints

- Stay inside `scope.json`.
- Add failure-injection tests before/with behavior changes.
- Do not weaken approval, expected SHA, base, or branch checks.
- Do not create an unrestricted external-state checkpoint store.

### Task 1: Exact publication recovery

- [x] Reproduce retry failure after prior branch publication.
- [x] Recover exact prior publication for absent and pre-existing expected branch cases.
- [x] Reject changed/conflicting remote branch state.

### Task 2: Exact PR recovery

- [x] Recover one exact open PR after response loss.
- [x] Inspect bounded PR history so closed/merged exact PRs are not recreated.
- [x] Preserve `OPEN_PULL_REQUEST_EXISTS` compatibility for conflicts.

### Task 3: Coordinator failure contract

- [x] Add stage/completed-step/retryable diagnostics.
- [x] Use structured error-code classification with conservative fallback.
- [x] Mark the public tool idempotent and test serialized diagnostics.

### Task 4: Verify and integrate

- [x] Run focused and workflow tests.
- [x] Run scope/diff checks and independent API review.
- [x] Run repository verification; exact-head CI remains pending PR publication.
- [ ] Merge, commission, reconcile #211, and clean the change.
