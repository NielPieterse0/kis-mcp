# Repository Scoped Work Management Projection Implementation Plan

**Goal:** Apply only the repository projection/binding correction established by executable #318 evidence.

**Architecture:** Keep the shared GitHub Project as authority. Enforce repository scope at the GitHub Project inventory projection and reconciliation routing boundary using the existing `ProjectBinding.repository` value.

**Tech Stack:** Python 3.13, pytest, GitHub Project adapters, governed KIS change workflow.

## Global constraints

- Stay inside `scope.json`.
- Add failing tests before production behavior changes.
- Do not edit `work_management/service.py`; active change 173 owns it.
- Do not touch execution/verification, coordinator, or housekeeping paths.
- Preserve explicit unbound cross-repository visibility.
- Preserve idempotency and revision/CAS behavior.
- Do not merge without exact-head GitHub Actions evidence.

## Task 1: Verify #318

- Exercise live inventory, next-work, preview mutation routing, hold/defer, readiness failure, and command contract surfaces.
- Run lifecycle, traceability, command-service, selection, reconciliation, and Project adapter tests.
- Classify each operation as correct, defect, missing, or stale assumption.
- Proceed to #317 only if repository routing is proven defective.
## Task 2: Repair #317

- Add repository-scoping and scoped-limit regression tests to the inventory adapter.
- Add CREATE/UPDATE tests proving foreign explicit repositories are rejected before provider calls.
- Implement repository filtering while scanning the shared Project page stream.
- Enforce the selected binding repository before reconciliation/idempotent execution.
- Retain `repository=None` as the explicit unscoped/cross-repository projection.

## Task 3: Verify and freeze

- Run focused provider and Work Management regressions.
- Run compile and Ruff checks.
- Run governed scope and diff checks.
- Obtain independent code-quality and API-contract reviews.
- Run canonical repository verification locally.
- Commit and prepare a reviewable candidate without merging while Actions is unavailable.