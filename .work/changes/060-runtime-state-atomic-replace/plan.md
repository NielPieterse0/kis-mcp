# Runtime State Atomic Replace Implementation Plan

> **For agentic workers:** Execute this plan task-by-task and keep the declared scope current.

**Goal:** Make repeated writes to per-instance `current.json` succeed on the active PowerShell/.NET runtime without changing lifecycle semantics.

**Architecture:** Keep `Write-KisMcpAtomicJson` as the single state writer. Preserve the existing write-to-sibling-temp-file pattern, but replace the destination with a same-filesystem overwrite move that does not require a backup path. No caller or lifecycle-state changes are required.

**Tech Stack:** PowerShell 7, .NET `System.IO.File`, Python pytest, existing KIS change governance.

## Global constraints

- Stay inside `scope.json`.
- Add the regression test before production code.
- Preserve `restarting`, `preflight_failed`, `startup_failed`, `ready`, and `stopped` semantics.
- Do not alter HR-001, HR-002, or HR-003.
- Do not touch `kis-op` during implementation verification.

---

### Task 1: Reproduce and fix existing-state replacement

**Files:**
- Modify: `scripts/startup-instance-lifecycle.ps1`
- Test: `tests/test_startup_scripts.py`

**Interfaces:**
- Consumes: `Write-KisMcpAtomicJson -Path <string> -Document <object>`.
- Produces: the same interface, with both create and overwrite behavior supported.

- [x] Add `test_startup_lifecycle_atomic_json_replaces_existing_file` that writes two documents to the same temporary path through the real PowerShell function and asserts the second document is persisted.
- [x] Run the startup test file before the production edit and confirm the new test fails because the persisted value remains `1` instead of `2`.
- [x] Change only the existing-destination branch of `Write-KisMcpAtomicJson` to a same-filesystem overwrite move that needs no backup path.
- [x] Rerun the new test and focused startup/tunnel tests; 39 passed.

### Task 2: Review, verify, and deliver

**Files:**
- Update: `.work/changes/060-runtime-state-atomic-replace/spec.md`
- Update: `.work/changes/060-runtime-state-atomic-replace/plan.md`
- Update: `.work/changes/060-runtime-state-atomic-replace/tasks.md`
- Update: `.work/changes/060-runtime-state-atomic-replace/closeout.md`

- [x] Review the final diff for scope, atomic-state semantics, temporary-file behavior, and policy neutrality.
- [x] Run `pwsh -NoProfile -File scripts/change-workflow.ps1 check`; passed.
- [x] Run `pwsh -NoProfile -File scripts/verify.ps1`; passed.
- [x] Record PR/merge/cleanup as post-commit delivery evidence reported separately from the committed implementation closeout.
- [x] Record live `development` restart as post-merge operator-supervised commissioning evidence rather than an unattended implementation gate.
