# Housekeeping Operationalization Implementation Plan

**Goal:** Commission Change 194 on the existing authenticated `kis-op` runtime with unattended preview scheduling, durable health evidence, and fail-closed supervised apply.

**Architecture:** Add an isolated `housekeeping_runtime` layer around the landed runner package. A lifecycle-only FastMCP provider starts one scheduler service after the gateway's existing providers enter their lifespans. The service calls the parent server through `FastMCPInvoker`, persists bounded state beneath the configured KIS state root, and exposes read-only status plus explicit receipt-bound apply. The scheduler activates only for `kis-op`.

**Tech stack:** Python 3.13, FastMCP 3.x, existing Work Management/GitHub provider runtime, strict JSON settings, asyncio, pytest, Ruff.

## Global constraints

- Stay inside `scope.json` and do not modify the landed `src/kis_mcp/housekeeping/**` algorithms.
- Keep scheduled execution preview-only.
- Reuse the existing authenticated provider runtime; do not introduce PAT, Actions mutation scheduling, or a second execution/landing authority.
- Persist generated operational evidence only under `C:\Projects\.kis-mcp`.
- Add focused tests before each behavior change.

### Task 1 — Settings and contracts

- Define strict settings for host identity, state namespace, retention, freshness, apply age, and runner targets.
- Validate repository roots remain beneath `C:\Projects`, targets are unique, intervals are bounded, and scheduled mode is immutable preview.
- Add focused parsing/validation tests.

### Task 2 — Durable state and stable apply identity

- Implement canonical receipt/plan fingerprinting and deterministic idempotency-key derivation.
- Implement atomic bounded receipt/failure/status persistence with retention.
- Add tests for replay identity, stale/invalid receipts, atomic state, and bounded retention.### Task 3 — Scheduler service and lifecycle host

- Implement one asyncio loop per enabled runner with injectable clock/sleep for deterministic tests.
- Run `scheduled` preview only, persist success/failure, calculate next due time, and survive individual runner failures.
- Add a lifecycle-only FastMCP provider that starts only when the normalized runtime instance is `kis-op` and cancels cleanly on shutdown.
- Add tests proving `kis-dev` inactivity, exact task count, failure isolation, cancellation, and cadence.

### Task 4 — Explicit supervised apply and status surface

- Add a read-only status tool backed by persisted scheduler state.
- Add explicit apply-by-receipt: load a fresh complete preview, rerun preview, compare actionable-plan fingerprint, derive stable idempotency key, then invoke the landed runner in apply mode.
- Persist apply success/failure independently and never make apply callable from the timer path.
- Add tests for stale/changed/incomplete receipt rejection and stable retry identity.

### Task 5 — Gateway/settings/documentation integration

- Register the lifecycle provider after existing GitHub/Work Management composition so it reuses active provider lifespans.
- Preserve the legacy Work Management `scheduled_reconciliation=false`; the new housekeeping runtime has its own explicit scheduler authority and status surface.
- Update `SPEC.md` current implementation truth and `docs/operations/work-discover.md` operator/status/apply guidance without duplicating settings values.
- Validate runtime tool exposure and no duplicate scheduler on `kis-dev`.

### Task 6 — Verification, publication, and live commissioning

- Run focused housekeeping-runtime tests, affected gateway/settings tests, Ruff, `git diff --check`, and `change-workflow.ps1 check`.
- Run required specialist reviews against the complete base-to-candidate range; resolve blocking findings and rerun invalidated checks.
- Freeze/publish one exact head and obtain canonical GitHub Actions success for that head before merge.
- Merge, align `main`, and run governed cleanup.
- Restart/authenticate live `kis-op` on merged `main`; prove both scheduled previews execute unattended and status/receipts remain fresh.
- Only after that proof reconcile Hold #379 and #364 complete. Change 195 remains preserved and unpublished until this boundary is satisfied.