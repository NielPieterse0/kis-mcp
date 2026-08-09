# Startup Runtime Reclaim Implementation Plan

> **For agentic workers:** Execute this plan task-by-task and keep the declared scope current.

**Goal:** Make selected-instance restart reliably reclaim the KIS runtime it owns while continuing to refuse unrelated port owners.

**Architecture:** Keep ownership resolution in `startup-instance-lifecycle.ps1`. Extend only the selected-server identity predicate so it accepts either the canonical executable path or a command line whose launch token is the canonical project Python path, while still requiring the exact `kis_mcp.remote_runtime --instance <selected>` invocation. Reuse the existing forceful process-tree stop and port-release wait rather than adding a second shutdown mechanism.

**Tech Stack:** PowerShell 7, Windows CIM process metadata, pytest.

## Global constraints

- Stay inside `scope.json`.
- Add the regression test before behavior changes and observe the expected RED result.
- Never kill a process based only on port number, executable name, or generic Python identity.
- Preserve peer-instance isolation and the exact three-rule policy boundary.

---

### Task 1: Prove and fix canonical runtime identity

**Files:**
- Modify: `scripts/startup-instance-lifecycle.ps1`
- Test: `tests/test_startup_scripts.py`

**Requirements:** REQ-001, REQ-002, REQ-003, REQ-004

- [ ] Add a regression test where `ExecutablePath` is the resolved base interpreter but `CommandLine` starts with the canonical project Python launcher and selected remote runtime.
- [ ] Run the focused test and confirm it fails because the current predicate rejects the process.
- [ ] Implement the smallest identity change that accepts the canonical command-line launch token while preserving exact module and instance checks.
- [ ] Run the focused lifecycle tests and confirm the regression is green.
- [ ] Review the stop path to confirm it still uses `Stop-Process -Force` and `Wait-KisMcpSelectedPortReleased` and that unrelated owners remain rejected.

### Task 2: Reconcile operator documentation

**Files:**
- Modify: `docs/OPERATIONS.md`
- Test: `tests/test_startup_scripts.py`

**Requirements:** REQ-005

- [ ] Update the existing startup lifecycle documentation to state that selected-instance ownership may be proven by the canonical project Python launch token even when Windows reports the underlying interpreter path.
- [ ] Preserve the documented refusal for unrelated port owners and peer-instance isolation.
- [ ] Run the documentation/startup focused tests.

### Task 3: Verify and close

**Files:**
- Modify: `.work/changes/082-startup-runtime-reclaim/tasks.md`
- Modify: `.work/changes/082-startup-runtime-reclaim/closeout.md`

**Requirements:** REQ-001 through REQ-005

- [ ] Run `pwsh -NoProfile -File scripts/change-workflow.ps1 check` from the change worktree.
- [ ] Run focused startup tests.
- [ ] Run `pwsh -NoProfile -File scripts/verify.ps1`.
- [ ] Review the final diff for scope, safety, and unnecessary complexity.
- [ ] Commit, merge through the governed repository workflow, clean the worktree, then start and commission fresh `kis-op` from clean `main`.
