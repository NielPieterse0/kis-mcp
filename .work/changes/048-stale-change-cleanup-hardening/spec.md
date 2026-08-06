# Specification: Stale Change Cleanup Hardening

## Outcome

Reconcile merged changes `041` and `046` as closed, preserve their complete Git and PR recovery evidence, and prevent the governed cleanup command from removing a worktree or branch until closure metadata has been committed and merged.

## Required behavior

1. Change records `041` and `046` report `closed` and their closeouts record exact merge and cleanup evidence.
2. Cleanup refuses a clean merged worktree when its own `scope.json` status is `active` or `ready`.
3. Cleanup succeeds only after the claim status is `closed`, the worktree is clean, and the branch is merged into its declared base.
4. Cleanup preview reports non-closed status as a blocker and does not advertise the change as eligible.
5. Validation continues to treat only `active` and `ready` claims as collision-bearing.
6. No policy, runtime capability, provider, credential, package, external state, or general operations documentation changes are introduced.
7. Worktrees and records for changes `040` and `047` remain untouched.

## Recovery

All source changes remain recoverable through Git. Cleanup may remove only the redundant merged worktree and local branch after the closure and merge gates pass. A failed worktree removal retains or moves remnants to the existing recoverable backup path; no permanent deletion is added.

## Verification

Use TDD for cleanup and preview behavior, run focused governance tests, validate scope, run `git diff --check`, and run the repository verification entry point before delivery.
