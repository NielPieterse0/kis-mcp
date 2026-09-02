# Lifecycle Decision Auto Recovery Implementation Plan

> **For agentic workers:** Execute task-by-task and keep scope/evidence current.

**Goal:** Make the once-through successor mechanically explicit and make expected-running KIS runtime recovery automatic and instance-scoped.

**Architecture:** Add a read-only lifecycle projection over existing `TaskHandoffStore` PromotionReady evidence plus the durable `PromotionStateStore` controller checkpoint; add a guard consumed by verification execution; generalize the independent recovery script around the existing instance-aware launcher; route post-land restart through that recovery surface. No new lifecycle authority or parallel state store.

**Tech stack:** Python 3.11, FastMCP, PowerShell 7, pytest, existing KIS change/Work/GitHub workflows.

## Tasks

### 1. Lifecycle decision contract
- Add regression tests for pre-promotion, PromotionReady, stale evidence, exact source/tree binding, canonical owners, and one next action.
- Implement the read-only decision service and MCP registration without modifying active Change 618-owned once-through files.

### 2. Redundant verification guard
- Add focused tests proving PromotionReady suppresses ordinary local canonical full verification and that a 502-equivalent redundant verifier failure is nonblocking.
- Project the valid successor from the existing promotion controller/checkpoint and retain observable prevented-operation evidence.

### 3. Runtime auto recovery
- Add tests first for generalized `kis-dev`/`kis-op` local-shell recovery, idempotence, health-triggered repair, readiness verification, durable receipts, and peer isolation.
- Route compatibility wrappers and post-land development refresh through the generalized primitive.

### 4. Integration and documentation
- Register the lifecycle operation/workflow metadata and reconcile `SPEC.md` plus scoped Operations runbooks.
- Run focused affected tests, specialist reviews, and `change-workflow.ps1 check`.
- Publish via `prepare_reviewable_pull_request`; consume exactly one canonical exact-head GitHub Actions run, merge readiness, merge, commissioning, Work completion, and cleanup.
