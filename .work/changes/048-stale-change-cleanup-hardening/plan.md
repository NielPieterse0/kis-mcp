# Stale Change Cleanup Hardening Plan

## Goal

Repair the stale merged claims and close the workflow gap that allowed cleanup before closure metadata was merged.

## Tasks

1. Characterize the current cleanup and cleanup-preview behavior with failing tests.
2. Add the smallest closure-status gates to cleanup and preview.
3. Reconcile change records `041` and `046` with exact merged-state evidence.
4. Run focused tests, governance validation, scope checks, whitespace checks, and full verification.
5. Commit, push, create and review a pull request, merge the exact verified head, verify merged `main`, then clean up only change `048`.

## Constraints

- Work only in `.work/worktrees/048-stale-change-cleanup-hardening`.
- Do not modify change `040`, change `047`, their worktrees, or their branches.
- Do not perform permanent deletion.
- Do not change HR-001, HR-002, or HR-003.
- Do not install packages or use external network through Work.
