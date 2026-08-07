# Closeout: CI Governance Validation

## Implemented scope

- Added explicit `require_active_worktrees` control to repository governance validation; default remains strict.
- Added `validate --claims-only` for isolated environments that cannot contain unrelated sibling worktrees.
- Updated the Work Management Windows workflow to use the explicit isolated claim-validation mode.
- Added regression coverage proving strict local validation still fails when an active worktree is missing.

## Validation evidence

- TDD red: isolated-mode test failed because `require_active_worktrees` did not exist.
- Focused checks: 23 governance/workflow tests passed.
- Repository verification: `scripts/verify.ps1` passed with pytest exit 0, syntax, configuration, dependencies, governance, and policy checks green.
- Diff scope check: `scripts/change-workflow.ps1 check` passed; `git diff --check` passed.

## Review

- Root cause: exact-head Work Management run #15 failed because an isolated GitHub Actions checkout inherited active change 063 but could not contain its unrelated local worktree.
- Resolution preserves local topology enforcement and changes only the CI invocation to an explicit claims-only mode.
- Unrelated active changes remain untouched.

## Git and merge

- Branch: `change/065-ci-governance-validation`
- Worktree: `.work/worktrees/065-ci-governance-validation`
- Verified head: `ac4d10d905360acdd77c9154a0e17b8990ae4cf5`.
- Exact-head Work Management run #16: success; settings, governance claims, focused P5 tests, and canonical verification all passed.
- Pull request: #83, merged.
- Merge commit: `507e95d84228b4f0fca9761aced53a5556c8932d`.
- Cleanup: eligible after this closeout bookkeeping lands on `main`.

## Residual items

- PR #80 must reconcile repaired `main`, pass a fresh exact-head Windows gate, merge, and complete post-merge P5 commissioning.
