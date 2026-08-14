# Tasks: Reconciled Branch Cleanup

- [x] Confirm authority and non-overlap with active change 125.
- [x] Reproduce the reconciled-branch false negative with tests.
- [x] Implement local landed-evidence classification and recoverable cleanup preparation.
- [x] Wire cleanup preparation into the canonical PowerShell workflow.
- [x] Run `pwsh -File scripts/change-workflow.ps1 check` and `git diff --check`.
- [x] Run the full affected `tests/test_git_workflow.py` suite.
- [ ] Pass exact-head Canonical Verification.
- [ ] Merge, synchronize local `main`, clean the change worktree, and close issue #178.
