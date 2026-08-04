# Tasks: 004-live-proxy-commissioning

- [x] Inspect authority, active worktrees, and claimed paths.
- [x] Create isolated worktree and establish green baseline.
- [x] Record approved specification and implementation plan.
- [x] Implement pure commissioning helpers test-first.
- [x] Implement and run the live stdio commissioning scenario.
- [x] Add the locked PowerShell commissioning entry point.
- [x] Add provider-state integrity detection and automatic snapshot restoration.
- [x] Run final change check, repository verification, diff review, and closeout.
- [x] Commit and raise an unmerged draft pull request.

## Blocking result

The functional proxy stages pass, but Desktop Commander `0.2.46` truncates its shared `config.json` during shutdown. The harness detects the invalid state, restores the pre-run snapshot atomically, and fails commissioning with `PROVIDER_STATE_INTEGRITY`.
