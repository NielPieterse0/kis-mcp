# Operational Status Closeout Implementation Plan

> **For agentic workers:** Execute task-by-task and keep scope current.

**Goal:** Replace two stale status indicators with bounded current-runtime evidence.

**Architecture:** Keep evidence process-local. Supabase routing marks only successful registered-project read calls; the provider readiness probe reads that state. Remote runtime exposes its selected instance process-locally; health reads the launcher-owned `current.json` and upgrades only a fully matching ready record.

**Tech Stack:** Python 3.13 runtime, FastMCP middleware, pytest, PowerShell repository verification.

## Global constraints

- Stay inside `scope.json`; do not overlap 040/084/085.
- Add failing tests before behavior changes.
- Do not edit static settings owned by 084.
- Do not alter HR-001/HR-002/HR-003 or provider authorization semantics.
- No external network actions and no push to `origin/main`.

### Task 1: RED tests

- Add focused tests under `tests/commissioning/` for Supabase live-verification transitions and remote health state validation.
- Confirm the tests fail against the current hard-coded behavior.

### Task 2: Supabase runtime evidence

- Add a minimal process-local commissioning state.
- Mark it only after successful registered-project read completion.
- Feed the state into `provider_health` through the existing descriptor lifecycle.

### Task 3: Remote runtime status evidence

- Record the selected remote instance in process-local environment for the lifetime of `run_remote_instance`.
- In `health_response`, inspect only the selected instance `current.json` beneath the canonical state root.
- Upgrade only `implementation_status.remote_mcp` when lifecycle, instance, endpoint, and listener PID match the current process.

### Task 4: Review and verification

- Run focused commissioning tests.
- Run `pwsh -File scripts/change-workflow.ps1 check` from the worktree.
- Inspect the final diff for scope, correctness, false positives, secrets, and policy drift.
- Run `pwsh -File scripts/verify.ps1`.
- Commit, merge locally into clean `main`, clean change 086, restart only `kis-op`, and repeat live provider/health checks through the actual ChatGPT-side tool.
