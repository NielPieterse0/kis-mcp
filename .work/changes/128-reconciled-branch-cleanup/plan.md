# Reconciled Branch Cleanup Implementation Plan

**Goal:** Make canonical cleanup safely normalize locally divergent but verifiably landed reconciled branches before non-forced worktree cleanup.

**Architecture:** Keep `change-governance.py` unchanged. Extend the local Git workflow with explicit landed-evidence classification and a cleanup-preparation step; have the canonical PowerShell wrapper invoke that step immediately before existing governance cleanup.

**Tech Stack:** Python, Git CLI, PowerShell, pytest.

## Global constraints

- Stay inside `scope.json`; do not touch 125-owned governance files.
- Preserve normal ancestry as the primary cleanup path.
- Require clean local state and deterministic local landing evidence before any branch normalization.
- Preserve the original branch head before normalization.
- Keep final worktree/branch removal delegated to existing non-forced cleanup.

### Task 1: Reproduce and classify

- [x] Add failing tests for a reconciled tree-equivalent branch and an unlanded branch.
- [x] Confirm the existing ancestry-only preview produces the wrong result.

### Task 2: Implement bounded preparation

- [x] Add ancestry, reachable-tree, and patch-equivalence landing evidence.
- [x] Add recoverable `prepare-cleanup` normalization using `reset --keep` and a recovery ref.
- [x] Invoke preparation from `change-workflow.ps1` only for cleanup commands.

### Task 3: Verify and land

- [x] Run focused `tests/test_git_workflow.py` coverage.
- [x] Run scope and diff checks.
- [ ] Run exact-head Canonical Verification through GitHub Actions.
- [ ] Merge, refresh local `main`, clean the 128 worktree, and close SPEC-128.
