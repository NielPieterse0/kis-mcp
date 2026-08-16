# Closeout: Work Management View Readback

## Implemented scope

- Retain each canonical Project view number and use it for bounded saved-view item readback.
- Require complete behavioral evidence for filtered canonical views before semantic readiness can be true.
- Reject contradictory, malformed, blank, or paginated-beyond-budget behavioral evidence as unready/unverified.
- Repair documented existing-view layout, filter, and visible-field drift in place; refuse unsupported sort/group/vertical-group drift and retain the no-delete/recreate boundary.
- Reapply a structurally matching filter once when behavioral readback contradicts it, then require a fresh structural and behavioral re-read before success.
- Reopen Work Management programme commissioning until #270 is proven live across all 12 canonical views.

## Validation evidence

- Focused checks: `pytest tests/providers/github/projects/test_schema_commissioning.py tests/work_management/test_schema.py tests/work_management/test_service.py -q` passed.
- Affected checks: `pytest tests/providers/github/projects tests/work_management -q` passed.
- Ruff: changed production/test files passed via the installed Ruff executable.
- Repository verification: pending exact-head GitHub Actions after PR creation.
- Diff scope check: `git diff --check` passed; `scripts/change-workflow.ps1 check` passed with all changed paths inside `scope.json`.

## Review

- Required reviews: `code-quality` and `api-contracts`.
- Findings: pending exact-source specialist review.
- Resolutions: pending.

## Git and merge

- Branch: `change/162-work-management-view-readback`
- Worktree: `.work/worktrees/162-work-management-view-readback`
- Commit:
- Pull request or merge:
- Cleanup:

## Residual items

-
