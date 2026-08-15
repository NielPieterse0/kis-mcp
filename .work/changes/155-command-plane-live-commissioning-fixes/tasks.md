# Tasks: Command Plane Live Commissioning Fixes

- [x] Confirm authority, live failure evidence, and non-overlapping governed scope.
- [x] Add red regressions for empty Project values and missing dependency schema.
- [x] Implement adapter normalization and `Blocked By` manifest correction.
- [x] Update authoritative schema/operations documentation.
- [x] Run focused and affected tests.
- [x] Run `git diff --check` and `pwsh -File scripts/change-workflow.ps1 check`.
- [x] Run canonical verification and required final reviews.
- [ ] Commit, publish exact-head PR, pass CI/readiness, and merge.
- [ ] Recommission live Project schema and run command-plane smoke.
- [ ] Close #142 with evidence and safely clean the change worktree.
