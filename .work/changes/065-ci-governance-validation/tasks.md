# Tasks: CI Governance Validation

- [x] Confirm authority, failure evidence, and bounded scope.
- [x] Add a failing regression for isolated validation while preserving strict local validation.
- [x] Implement explicit `validate --claims-only` behavior and opt Work Management CI into it.
- [x] Run focused governance/workflow tests: 23 passed.
- [x] Run `scripts/change-workflow.ps1 check` and `git diff --check`.
- [x] Run canonical `scripts/verify.ps1`: passed.
- [x] Commit, push, review, and merge the exact verified head via PR #83.
- [x] Hand repaired `main` back to PR #80 for a fresh exact-head reconciliation and Windows gate.
- [x] Close change 065 and make its merged worktree eligible for governed cleanup.
