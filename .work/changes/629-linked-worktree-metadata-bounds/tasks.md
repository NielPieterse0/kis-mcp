# Tasks: Linked Worktree Metadata Bounds

- [x] Confirm authority and scope.
- [x] Add regressions for legitimate large active config and packed-refs.
- [x] Add fail-closed regressions above the collection budget.
- [x] Implement separate control and collection metadata byte budgets.
- [x] Preserve control-pointer, boundary, identity, symlink/reparse, and bounded-read safety.
- [x] Run `pwsh -File scripts/change-workflow.ps1 check`.
- [x] Run focused `tests/discover/test_git_reader.py` verification: 15 passed.
- [ ] Obtain final exact-source code-quality review: PASS.
- [ ] Obtain final exact-source safety-security review: PASS.
- [ ] Run final repository verification on the reconciled exact source.
- [ ] Publish and merge after exact-head GitHub Actions success.
- [ ] Verify corrected KIS runtime against commodity #289.
- [ ] Run governed cleanup for only merged-and-clean obsolete worktrees.