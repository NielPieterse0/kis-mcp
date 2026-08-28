# State Ownership Diagnostics Cleanup Implementation Plan

**Goal:** Complete #550 with bounded state diagnostics and recoverable stale reconstructible-state cleanup.

**Architecture:** Add one diagnostics service beside the canonical state contract. It classifies only contract-shaped namespaces, determines source staleness from registered project/current worktree identities, fences registered-project cleanup with the repository change-admission lock, and delegates recoverable mutation to the signed quarantine service with pre-move intent journaling. Mount two local operator tools through the workflow platform.

**Tech Stack:** Python 3.13, FastMCP 4 runtime tools, existing Project registry, existing `QuarantineService`, pytest.

## Global constraints

- Stay inside `scope.json`.
- Do not read state payload contents for diagnostics.
- Do not invent ownership classes or namespace semantics.
- Never permanently delete state; apply is quarantine-only.
- Treat uncertain/runtime liveness as unsafe for cleanup.

### Task 1: Diagnostics contract

- [x] Add tests for canonical ownership classification and no payload-content exposure.
- [x] Implement bounded inventory with age/provenance and unclassified-root reporting.
- [x] Detect stale registered-project/source identities conservatively.

### Task 2: Recoverable cleanup

- [x] Test preview, preview-token enforcement, quarantine apply, replay idempotency and authoritative-state refusal.
- [x] Restrict eligibility to proven-stale registered-project `reconstructible-cache` sources; keep unregistered-project cache diagnostic-only.
- [x] Bind apply to the exact path identity observed by a short-lived preview token and hold the repository admission lock through commit.
- [x] Reuse signed quarantine/restore semantics with a signed write-through pre-move intent for interruption recovery.

### Task 3: Operator surface

- [x] Expose local `state_ownership_inventory`.
- [x] Expose preview-first `state_stale_cleanup`; require idempotency key and prior preview token for apply.
- [x] Register discoverable state inspection/cleanup workflows.
- [x] Verify tool annotations keep the surface local and recoverable.

### Task 4: Governed closeout

- [x] Run focused state/tool/platform regression tests.
- [ ] Run change governance and specialist reviews.
- [ ] Publish exact commit and pass exact-head GitHub Actions.
- [ ] Merge, live-commission the landed tools, complete #550/#491 as eligible, and clean Change 256.
