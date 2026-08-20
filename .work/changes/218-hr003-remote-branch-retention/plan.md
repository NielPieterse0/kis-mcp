# HR-003 Remote Branch Retention Implementation Plan

**Goal:** remove destructive remote branch deletion from normal KIS PR closeout and from the public registered GitHub mutation surface.

**Architecture:** keep merge and verified default-branch refresh unchanged; retain remote review branches. Remove the delete virtual descriptor, schema, dispatcher path, and destructive service method. Make unsupported delete dispatch fail closed through the existing unknown-operation guard.

**Tech Stack:** Python 3, pytest, KIS capability catalogue/workflows, registered GitHub exact operations, PowerShell change governance.

## Global constraints

- Stay inside `scope.json`; do not touch `SPEC.md` or Change 217 coordinator paths.
- Add/adjust focused tests before production behavior changes.
- Do not weaken HR-001/HR-002 or reinterpret HR-003.
- Do not use `destructiveHint` or tool-name heuristics as policy authority.

### Task 1: Encode failing contract tests

**Files:**
- `tests/capabilities/test_registered_commit_workflow.py`
- `tests/capabilities/test_registered_default_branch_refresh_capability.py`
- `tests/workflows/test_registered_commit_publication.py`

- [ ] Require the registered delete operation/schema to be absent.
- [ ] Require closeout to retain the remote branch after refresh.
- [ ] Require direct dispatch of the removed operation to fail before mutation.
- [ ] Run the focused tests and capture the expected RED result.
### Task 2: Remove destructive Work authority

**Files:**
- `src/kis_mcp/capabilities/surface.py`
- `src/kis_mcp/workflows/platform.py`
- `src/kis_mcp/projects/github_exact.py`

- [ ] Remove the registered delete virtual descriptor and public schema.
- [ ] Remove destructive service/dispatch behavior.
- [ ] Rewrite safe closeout to retain remote branches.
- [ ] Keep `delete_branch_on_merge=false` repository policy unchanged.

### Task 3: Reconcile trust authority and audit

**Files:**
- `docs/TRUST-MODEL.md`

- [ ] Remove registered branch deletion from the supervised mutation table.
- [ ] State remote review-branch retention semantics for normal closeout.
- [ ] Audit currently exposed external delete operations and record any residual provider-boundary findings under #431/#419.

### Task 4: Verify and close

- [ ] Run focused pytest files.
- [ ] Run `pwsh -File scripts/change-workflow.ps1 check`.
- [ ] Run required specialist reviews from risk triggers.
- [ ] Commit, publish, exact-head CI, merge readiness, merge, refresh main, reconcile Work Management/docs, and governed cleanup without remote branch deletion.
