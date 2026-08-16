# Work Management View Readback Implementation Plan

> **For agentic workers:** Execute this plan task-by-task and keep the declared scope current.

**Goal:** Make semantic readiness prove the records returned by each saved GitHub Project view, not only the stored view configuration.

**Architecture:** Extend the existing bounded `GitHubProjectSchemaClient` snapshot with view numbers, read saved-view items through GitHub's 2026-03-10 Project REST contract, evaluate the canonical manifest filter grammar against returned Project field values, follow cursor pagination within a fixed evidence budget, and require both structural and behavioral evidence before commissioner success.

**Tech Stack:** Python 3.11+, `gh api` through the existing registered GitHub client boundary, pytest, Ruff, change workflow.

## Global constraints

- Stay inside `scope.json`.
- Add failing regressions before behavior changes.
- Preserve current view IDs and item IDs; no delete/recreate path.
- Do not absorb unrelated lanes or repository cleanup.
- Fail closed as unverified for incomplete behavioral evidence.

---

### Task 1: Lock the false-green regression

**Files:**
- Modify: `tests/providers/github/projects/test_schema_commissioning.py`
- Modify: `tests/work_management/test_service.py` only if service propagation needs coverage.

- [x] Add a snapshot fixture with a numeric view number.
- [x] Add saved-view item evidence contradicting `status:Inbox`.
- [x] Prove the prior implementation lacked the required behavioral read.

### Task 2: Add bounded behavioral readback

**Files:**
- Modify: `src/kis_mcp/providers/github/projects/schema_commissioning.py`
- Test: `tests/providers/github/projects/test_schema_commissioning.py`

- [x] Parse and retain `ProjectV2View.number` from GraphQL.
- [x] Add fixed-shape saved-view-items reads for user/org registered targets.
- [x] Request only required manifest field database IDs.
- [x] Reject blank/malformed response evidence instead of treating it as an empty view.
- [x] Evaluate supported canonical filter qualifiers and surface contradiction evidence.
- [x] Follow explicit `after` cursor pagination at 100 items per page within a fixed 10-page / 1000-item budget.
- [x] Detect malformed pagination, cursor cycles, provider failures, and budget exhaustion as bounded unverified reason codes; do not use unbounded `--paginate`.

### Task 3: Bind commissioning success to behavioral evidence

- [x] Require behavioral verification after structural preflight and after any supported mutation.
- [x] Ensure a structural match plus behavioral mismatch cannot return `ready=true`.
- [x] Repair existing layout/filter/visible-field drift in place through the documented `updateProjectV2View` input.
- [x] Keep sort/group/vertical-group drift explicit and unready because the current update input does not expose those dimensions.
- [x] Reapply the declared filter once when saved-view behavior contradicts a structurally matching filter, then require fresh behavioral verification.
- [x] Return bounded diagnostic evidence sufficient to distinguish semantic contradiction from incomplete provider evidence.

### Task 4: Verify, review, land, and recommission

- [x] Land initial behavioral-readback implementation through PR #293.
- [x] Land malformed/duplicate-field evidence hardening through authoritative-branch PR #295.
- [x] Reproduce post-merge acceptance failure on the landed runtime: seven views remained unverified with no semantic contradiction; `12 Completed` was confirmed pagination-limited.
- [x] Add red→green bounded pagination and diagnostic regressions; focused provider tests and affected Work Management tests passed in the interrupted same-lane work.
- [ ] Run exact-head CI and final review on the reconstructed pagination/diagnostic tranche.
- [ ] Merge the final exact head and restart/rebind runtime to the landed revision.
- [ ] Rerun bounded Project commissioning and behavioral acceptance for all 12 views using the new reason codes if any view remains unverified.
- [ ] Reconcile only evidence-backed legacy `Todo` / `In Progress` operational drift without blind mapping.
- [ ] Record final #270/#142 evidence, close #270 only if live acceptance is green, and safely clean the change.
