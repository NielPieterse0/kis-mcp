# Closeout: Merge Commit Delta Inspection

## Implemented scope

- Two-parent merge commits are inspected as the exact first-parent-to-merge delta.
- Commits with more than two parents fail closed with `GIT_UNSUPPORTED_MERGE_COMMIT`.
- Ordinary commit/range/branch behavior remains unchanged.
- Added regressions for merged payload retention and multi-parent rejection.

## Validation evidence

- Focused `tests/discover/test_change_targets.py`: 15 passed.
- Broader `tests/discover`: passed with one existing skip.
- Ruff on changed Python paths: passed.
- Diff/governance scope check: passed.
- Canonical repository verification: delegated to exact PR-head GitHub Actions per repository contract.

## Review

- Code-quality review initially found commit-identity consistency issues; implementation was corrected to use the verified immutable commit identity.
- Code-quality re-review: zero findings.
- API-contract review confirmed the two intentional #407 behavior changes; no additional defect was identified.
- Resolutions: all blocking implementation findings resolved and affected checks rerun.

## Git and merge

- Branch: `change/212-merge-commit-delta-inspection`
- Worktree: `.work/worktrees/212-merge-commit-delta-inspection`
- Commit:
- Pull request or merge:
- Cleanup:

## Residual items

-
