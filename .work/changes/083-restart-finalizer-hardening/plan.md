# Restart Finalizer Hardening Implementation Plan

**Goal:** Prevent a displaced launcher from failing when replacement startup owns the current state handoff.

**Architecture:** Keep state ownership in `Set-KisMcpCurrentInstanceStopped`. Before reading `run_id`, explicitly require that the parsed hashtable contains that key; if not, treat the state as newer/non-owned and return without mutation.

**Tech Stack:** PowerShell 7, pytest.

## Constraints

- Stay inside declared scope.
- Test first and observe RED before implementation.
- Do not change reclaim, process termination, port checks, or provider behavior.

### Task 1: Harden stopped-state ownership guard

- [ ] Add a regression test for `restarting` state without `run_id`.
- [ ] Run the test and confirm the current implementation fails under StrictMode.
- [ ] Add the minimal missing-key guard.
- [ ] Run focused startup tests.
- [ ] Run change-scope and canonical verification, review, commit, merge locally, and clean the worktree.
- [ ] Repeat the live self-restart and verify the old launcher exits without the prior finalizer error while the replacement reaches ready.
