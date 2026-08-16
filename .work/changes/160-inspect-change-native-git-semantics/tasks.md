# Tasks: Inspect Change Native Git Semantics

- [x] Confirm repository authority, issue #273 scope, and active-path isolation.
- [x] Reproduce native Git `0` changes versus KIS `200` false tracked modifications in a linked worktree.
- [x] Prove system/global Git line-ending configuration suppression is causal and stale/shared state is not.
- [x] Add failing linked-worktree regression tests for clean, staged, unstaged, untracked, repository-attribute, and hardening semantics.
- [x] Implement bounded effective line-ending configuration replay.
- [x] Run affected Discover tests, Ruff, and `git diff --check`.
- [x] Run canonical repository verification and `pwsh -File scripts/change-workflow.ps1 check`.
- [x] Review and record closeout evidence.
- [ ] Commit, prepare PR, verify exact-head CI, merge, and clean up the governed change.
