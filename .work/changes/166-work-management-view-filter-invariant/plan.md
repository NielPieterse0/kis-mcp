# Work Management View Filter Invariant Implementation Plan

**Goal:** Correct the canonical view authority, prevent recurrence, and recommission all 12 live saved views.

**Architecture:** Keep `github-project-schema.json` as desired-state authority. Add one load-time invariant in `work_management/schema.py` so a canonical view without a current-lifecycle `status:` qualifier is invalid before comparison or commissioning. Reuse the existing bounded commissioner and behavioral saved-view readback for live repair/acceptance.

**Tech Stack:** Python 3, strict JSON manifest, pytest, existing registered GitHub Project commissioner, PowerShell change governance.

## Global constraints

- Stay inside `scope.json`; do not touch change 159 `SPEC.md` ownership.
- Test first for the manifest invariant and intended filter set.
- Preserve all Project item identities and view identities.
- No delete/recreate path and no arbitrary GitHub API passthrough.

### Task 1: Lock REQ-007 in tests

- Add a failing test requiring all 12 canonical filters to contain one `status:` qualifier whose values are a subset of canonical Status options.
- Add explicit assertions for purpose-specific lifecycle subsets.
- Observe the current manifest fail because views 04, 05, 06, 09, 10, and 11 omit Status.

### Task 2: Correct manifest and loader

- Add bounded filter-token parsing for the canonical load-time lifecycle invariant.
- Update all affected view filters; broad views enumerate all canonical statuses.
- Keep existing layout, visible-field order, and Delivery Board vertical grouping unchanged.
### Task 3: Verify locally and review

- Run focused Work Management schema tests, affected commissioner/service tests if needed, Ruff/compile, `git diff --check`, and `scripts/change-workflow.ps1 check`.
- Run required code-quality and API-contract reviews on the exact source and resolve blocking findings.

### Task 4: Land and recommission

- Publish only the reviewed exact commit through the registered GitHub path and require exact-head Actions success.
- Merge, refresh `main`, restart/rebind `kis-dev` if required, and rerun registered Project commissioning.
- Require all 12 behavioral view checks green and schema plan empty.
- Reconcile evidence-backed legacy lifecycle drift only; do not bulk-map ambiguous Todo backlog.
- Reconcile programme metadata, #270/#142 evidence, and safely clean the change.