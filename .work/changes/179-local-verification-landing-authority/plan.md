# Local Verification Landing Authority Implementation Plan

> **For agentic workers:** Execute this plan task-by-task and keep the declared scope current.

**Goal:** Restore governed repository throughput without GitHub Actions by making KIS local exact-head verification the canonical landing evidence while preserving exact registered GitHub merge identity.

**Architecture:** Keep the current source-verification → exact-tree reconciliation → PR publication chain. Replace only the final Actions-dependent landing gate: after publication, run KIS verification against the exact reconciled PR-head commit, persist/reference that result in the implementation trace, require it in Work Management merge readiness, then merge only the explicitly approved PR head. Retire Actions-backed merge-queue workflows from the canonical catalogue rather than redesigning the queue in this emergency slice.

**Tech Stack:** Python 3.13, KIS workflow descriptors, provider-neutral Work Management traceability contracts, PowerShell repository verification, exact registered GitHub operations.

## Global constraints

- Stay inside `scope.json`.
- Add/adjust failing tests before behavior changes.
- Do not modify `.github/workflows/**`.
- Do not weaken exact-head merge, documentation, review, or change-scope gates.
- Do not mix Windows VM provider work into this slice.

---

### Task 0: Restore canonical pytest collection on merged baseline

**Files:**
- Add: `tests/execution/__init__.py`
- Modify: `src/kis_mcp/workflows/project_management/__init__.py`

- [x] Add only the package marker required to prevent duplicate top-level pytest module identities introduced by the merged execution tests.
- [x] Reorder the project-management package exports so parsing contracts are available before descriptor/capability imports can re-enter through the dormant merge-queue path.
- [x] Confirm full-suite collection proceeds past both the duplicate-module errors and the project-management circular import.

### Task 1: Prove the replacement merge-readiness contract

**Files:**
- Modify: `tests/workflows/project_management/test_documentation_tools.py`
- Modify: `src/kis_mcp/work_management/traceability.py`

- [x] Add tests proving exact-head referenced local verification passes.
- [x] Add tests proving Actions-only, stale, failed, and unreferenced local evidence fail closed.
- [x] Confirm the new expectations fail against the old Actions rule.
- [x] Implement the smallest merge-readiness correction.

### Task 2: Replace Actions-dependent completion workflow descriptors

**Files:**
- Modify: `src/kis_mcp/workflows/platform.py`
- Modify: `src/kis_mcp/workflows/project_management/descriptors.py`
- Modify: `tests/capabilities/test_registered_commit_workflow.py`
- Modify: `tests/capabilities/test_registered_default_branch_refresh_capability.py`
- Modify: `tests/workflows/project_management/test_descriptors.py`
- Modify: `tests/workflows/test_github_merge_queue_workflow.py`

- [x] Require local exact-head `execute_change_workflow` evidence in normal safe closeout.
- [x] Remove GitHub Actions read steps/capability from normal PR completion.
- [x] Remove Actions-backed speculative queue workflows from the canonical workflow catalogue while leaving implementation files untouched.
- [x] Preserve merge, refresh, documentation reconciliation, and cleanup ordering.

### Task 3: Reconcile repository authority documentation

**Files:**
- Modify: `AGENTS.md`
- Modify: `SPEC.md`
- Modify: `docs/PLATFORM-CONCEPT.md`
- Modify: `docs/operations/verification-changes.md`

- [x] State local KIS exact-head verification as canonical landing evidence.
- [x] Preserve GitHub as PR/head/merge control plane rather than verification executor.
- [x] Mark Actions queue/runner paths dormant/retired from canonical delivery.
- [x] Keep the Windows execution roadmap separate: #330 still owns live disposable Windows commissioning, subject to host/provider compatibility.

### Task 4: Verify, review, publish, and land

- [x] Run focused Work Management/workflow tests.
- [x] Run `pwsh -NoProfile -File scripts/change-workflow.ps1 check`.
- [x] Run `git diff --check`.
- [ ] Run full `pwsh -NoProfile -File scripts/verify.ps1` on the exact change commit; the pre-commit frozen candidate already passes the full verifier.
- [x] Complete code-quality and architecture/public-contract review; architecture used the governed manual exact-diff fallback after specialist timeouts.
- [ ] Prepare the exact verified commit as a PR, locally verify the reconciled exact PR head, merge only that head, refresh `main`, and clean the change.
