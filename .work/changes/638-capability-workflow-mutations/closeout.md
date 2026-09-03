# Closeout: Capability Workflow Mutations

## Implemented scope
- Added discoverable virtual `create_change_worktree` and `commit_change` operations.
- Routed both through `execute_change_action` without exposing new direct tools.
- Worktree creation delegates to the repository's governed change workflow.
- Commit creation requires a `change/*` branch and explicit safe relative pathspecs.

## Validation evidence
- Focused: 38/38 capability, dispatcher, composition, and governed-change tests passed.
- Scope: `pwsh -File scripts/change-workflow.ps1 check` passed.
- Canonical repository verification: deferred to exact-head PR Actions per `AGENTS.md`.

## Review
- API-contract review: zero findings.
- Code-quality review: one claimed Git diff return-code defect was disproved against the implementation; regression tests now explicitly prove return code 1 proceeds and return code 0 rejects no-op commits.

## Git and merge
- Branch: `change/638-capability-workflow-mutations`
- Worktree: `.work/worktrees/638-capability-workflow-mutations`
- Commit: pending
- Pull request/merge: pending
- Cleanup: pending

## Residual items
- `list_worktrees`, `cleanup_change_worktree`, and broader workflow catalogue reconciliation remain intentionally out of scope until this development path is live.
