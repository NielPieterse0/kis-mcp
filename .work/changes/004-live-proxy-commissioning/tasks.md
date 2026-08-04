# Tasks: 004-live-proxy-commissioning

- [x] Inspect authority, active worktrees, and claimed paths.
- [x] Create isolated worktree and establish green baseline.
- [x] Record approved specification and implementation plan.
- [x] Implement pure commissioning helpers test-first.
- [x] Implement and run the live stdio commissioning scenario.
- [x] Add the locked PowerShell commissioning entry point.
- [x] Add provider-state integrity detection and automatic snapshot restoration.
- [x] Raise draft pull request `#3` without merging.
- [x] Integrate current `main` containing the provider-state atomicity fix.
- [x] Rerun normal repository verification on the integrated head.
- [x] Rerun live commissioning successfully without provider-state restoration.
- [x] Pass final scope, whitespace, and diff review.
- [x] Reconcile closeout and specification evidence.

## Completion result

All functional proxy stages and provider-state integrity validation pass on current `main`. The commissioning command exits successfully without invoking snapshot restoration. No production gateway files are changed by this commissioning slice, and no merge blocker remains.
