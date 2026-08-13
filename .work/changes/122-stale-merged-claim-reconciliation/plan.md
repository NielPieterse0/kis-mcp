# Stale Merged Claim Reconciliation Plan

1. Verify GitHub merge state for the implementation PRs of changes 115-119.
2. Create isolated 122 worktree from exact current `main`; record the bootstrap exception.
3. Change only `status: active` to `status: closed` in the five historical scope records.
4. Run claim-conflict validation, scope check, `git diff --check`, and canonical repository verification.
5. Review the exact diff; commit and publish through the registered GitHub workflow.
6. Verify exact-head CI, merge, refresh registered tracking, synchronize local `main`, and clean the 122 worktree.
7. Leave all source issues and Project operator holds unchanged.
