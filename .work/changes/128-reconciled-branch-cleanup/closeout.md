# Closeout: Reconciled Branch Cleanup

## Implemented scope

- Cleanup preview now recognizes normal ancestry, exact reachable-tree equivalence, and all-patch equivalence.
- `prepare-cleanup` preserves the original branch head under `refs/kis-recovery/cleanup/<change-id>` before any normalization.
- Non-ancestor landed branches are normalized with `git reset --keep` to the exact verified base SHA, after which existing governance cleanup performs non-forced removal.
- `change-workflow.ps1 cleanup` invokes the preparation automatically.
- Divergent/unlanded branches remain blocked without branch mutation or recovery-ref creation.

## Validation evidence

- Focused checks: `tests/test_git_workflow.py` — 21 passed.
- Repository verification: pending exact-head GitHub Actions Canonical Verification.
- Diff scope check: passed; `git diff --check` passed.
- Ruff: local shared environment does not include Ruff; canonical CI remains authoritative for lint/full verification.

## Review

- Findings: initial tree-equivalence test assumed the specific reconciled parent would be returned, but the merge commit can legitimately carry the same tree.
- Resolutions: assertion now verifies the returned reachable commit has the exact source tree rather than depending on commit ordering.

## Git and merge

- Branch: `change/128-reconciled-branch-cleanup`
- Worktree: `.work/worktrees/128-reconciled-branch-cleanup`
- Commit: pending final commit.
- Pull request or merge: pending.
- Cleanup: pending after merge.

## Residual items

- None in this slice; `scripts/change-governance.py` remains untouched because active change 125 owns it.
