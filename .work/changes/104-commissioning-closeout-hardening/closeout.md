# Closeout: Commissioning Closeout Hardening

## Implemented scope

- `change-workflow new` now writes tracked lifecycle artifacts with canonical LF bytes on Windows.
- Added approval-gated `kis_github_reconcile_registered_commit`, which preserves the exact source tree on a verified remote-default parent and publishes only to a non-default review branch with an exact ref lease.
- Added discoverable capability exposure and reconciled existing `SPEC.md` / `docs/OPERATIONS.md` owners without changing HR-001/002/003.

## Validation evidence

- Focused governance/publication/capability regression set: 39 passed.
- `scripts/change-workflow.ps1 check`: passed for all 13 declared 104 paths.
- `git diff 0fa23f6..HEAD --check`: passed on the committed implementation.
- Sequential canonical `pwsh -NoProfile -File scripts/verify.ps1`: passed; full pytest exit 0 with two expected skips, 264 Python files syntax-checked, governance/configuration/dependencies and HR-001/002/003 green.

## Review

- Manual spec/code/test review verified approval gating, source-base ancestry, exact tree equality, stale/default ref rejection, non-default publication, exact leases, fixed provenance message, and publication verification.
- The running reviewer surface is working-tree-only and the resumed implementation was already committed; no independent-review pass is claimed for that committed diff.

## Git and merge

- Branch: `change/104-commissioning-closeout-hardening`
- Worktree: `.work/worktrees/104-commissioning-closeout-hardening`
- Implementation commit: `0767f680e3b8649079f0e54c6ea0e013e83a51e9`.
- Lifecycle reconciliation commit: pending final verification.
- Pull request/merge and cleanup: pending exact remote-main-rooted delivery.

## Residual items

- Pre-implementation red-test output was not preserved in the resumed committed worktree; final regression and canonical evidence remain required.