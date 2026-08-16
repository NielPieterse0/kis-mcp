# Work Management View Semantics Implementation Plan

> **For agentic workers:** Execute this plan task-by-task and keep the declared scope current.

**Goal:** Make the 12 canonical Work Management views semantically configured, repairable, and readiness-verifiable.

**Architecture:** Extend the provider-neutral Project view contract with declarative filter/display semantics. Extend the bounded registered-GitHub commissioner to read those semantics, update existing views in place using fixed GitHub API shapes, and create missing views with resolved field IDs. Feed the same normalized observations into schema status so commissioning and ordinary readiness use one comparison contract.

**Tech Stack:** Python 3, strict JSON manifest, GitHub Projects GraphQL/REST through the existing `gh` exact-operation boundary, pytest, PowerShell change governance.

## Global constraints

- Stay inside `scope.json`; do not touch paths owned by active changes 150 or 156.
- TDD: add a failing regression and observe the intended failure before each behavior change.
- No arbitrary API path/query/token surface and no Project/view deletion.
- Preserve Project item identities, existing field values, and single-select option IDs.
- Exact-head GitHub Actions remains canonical landing verification.

---

### Task 1: Make view semantics part of the manifest contract

**Files:** `settings/work-management/github-project-schema.json`, `src/kis_mcp/work_management/schema.py`, `tests/work_management/test_schema.py`

- [ ] Add failing manifest/schema tests for filter, visible fields, sort/group, and vertical board grouping.
- [ ] Confirm current parser rejects/ignores the new semantic keys and name-only observations falsely pass.
- [ ] Add strict typed view semantic contracts and deterministic drift reporting.
- [ ] Define all 12 canonical view filters and bounded display semantics.
- [ ] Run the schema-focused tests green.

### Task 2: Read and repair semantic view configuration

**Files:** `src/kis_mcp/providers/github/projects/schema_commissioning.py`, `tests/providers/github/projects/test_schema_commissioning.py`

- [ ] Add failing snapshot tests for filter/visible/sort/group/vertical-group parsing and mismatches.
- [ ] Extend the fixed snapshot query and normalized view model.
- [ ] Add in-place fixed-shape updates for API-supported semantics and complete semantics for missing-view creation.
- [ ] Require post-mutation semantic equality before `ready=true`.
- [ ] Run commissioner tests green.

### Task 3: Propagate semantic observations through Work Management

**Files:** `src/kis_mcp/work_management/service.py`, `src/kis_mcp/work_management/__init__.py`, `tests/work_management/test_service.py`

- [ ] Add a failing service test proving a correct name with a wrong filter is not ready.
- [ ] Return normalized semantic observations from `read_schema_views` and pass them unchanged into schema comparison.
- [ ] Preserve explicit `views_ready=None` only when the backend cannot observe views at all.
- [ ] Run affected Work Management tests green.

### Task 4: Reconcile programme evidence and verify the governed change

**Files:** `.work/programmes/work-management/**`, `docs/development/github-project-onboarding/commissioning.md`, `.work/changes/157-work-management-view-semantics/**`

- [ ] Replace stale provider-gap/schema-shell claims with the exact semantic commissioning contract.
- [ ] Run focused tests, exact-file Ruff/compile checks, `git diff --check`, and `scripts/change-workflow.ps1 check`.
- [ ] Run classification-required specialist reviews and resolve all blocking findings.
- [ ] Commit the exact reviewed tree and prepare an exact-head PR through KIS.

### Task 5: Land and live-commission the final closure

- [ ] Require provider-native exact-head CI and Work Management merge readiness.
- [ ] Merge through the governed registered-repository path and refresh `main`.
- [ ] Restart a KIS runtime on the merged revision and recommission Project #1.
- [ ] Re-read all 12 views and require semantic `views_ready=true` plus an empty schema plan.
- [ ] Verify representative live views (`01`, `03`, `08`, `12`) against their canonical filters/configuration.
- [ ] Record post-merge documentation reconciliation, complete #270, add final evidence to #142, and safely clean the worktree/remote branch.
