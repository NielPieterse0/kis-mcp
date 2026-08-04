# Startup Hardening Implementation Plan

> **For agentic workers:** execute task-by-task with TDD, review each task against this plan, and rerun affected checks after every repair.

**Goal:** Deliver deterministic, quiet, correctly classified startup for the ChatGPT tunnel path while containing Desktop Commander startup internals.

**Architecture:** Add one bounded Node preload compatibility adapter alongside the existing atomic-state adapter. Keep provider requests, results, tool names, and schemas unchanged; suppress provider log notifications; satisfy the exact feature-flag URL locally; strip only provider UI metadata from `tools/list` at the transport boundary; store tunnel secrets in Windows Credential Manager; and make PowerShell setup/start scripts own sequencing, transient credential injection, and error classification. Do not modify Work middleware or the Desktop Commander effect resolver.

**Tech stack:** Python 3.13, FastMCP 3.4.4, MCP Python SDK, Node.js CommonJS preload adapters, PowerShell 7, pytest.

## Global constraints

- Policy remains exactly HR-001, HR-002, and HR-003.
- Do not modify or vendor Desktop Commander.
- Do not change `src/kis_mcp/middleware.py` or `src/kis_mcp/desktop_commander.py`.
- Do not commit credentials, generated profiles, caches, or runtime state.
- Preserve ordinary Work tool contracts and results.
- All writes remain beneath `C:\Projects` and deletion remains recoverable.
- Change `007-chatgpt-remote-commissioning` is closed; change `013-startup-hardening` owns all further startup compatibility and launcher corrections listed in its scope.

---

### Task 1: Provider startup compatibility adapter

**Files:**
- Create: `src/kis_mcp/provider_startup_compat.cjs`
- Modify: `src/kis_mcp/provider_lifecycle.py`
- Test: `tests/test_provider_lifecycle.py`
- Test: `tests/test_startup_hardening.py`

**Interfaces:**
- Consumes: `KIS_MCP_PROVIDER_FLAG_URL`, Node `global.fetch`, `process.stdout.write`, and provider `tools/list` responses.
- Produces: deterministic local feature-flag responses, JSON-RPC log-notification suppression, and provider UI metadata removal while preserving all provider tool names and schemas.

- [x] Add failing Node-backed tests for exact feature-flag containment, unrelated fetch passthrough, notification suppression, ordinary JSON-RPC passthrough, metadata removal, and administration-tool preservation.
- [x] Implement the minimal CommonJS adapter with dependency-injection hooks for tests.
- [x] Preload startup compatibility after the atomic state adapter and set the exact flag URL environment value.
- [x] Add a seam-locality test proving compatibility behavior is absent from Work middleware and the effect resolver.
- [x] Run focused tests to green.

### Task 2: Quiet HTTP runtime

**Files:**
- Modify: `src/kis_mcp/remote_runtime.py`
- Test: `tests/test_remote_runtime.py`

**Interfaces:**
- Consumes: settings-defined remote instance and `FastMCP.run`.
- Produces: HTTP runtime invocation with `show_banner=False`.

- [x] Change the existing runtime expectation to require a disabled banner and verify it fails.
- [x] Set `show_banner=False`.
- [x] Run focused runtime tests to green.

### Task 3: Tunnel profile generation and readiness classification

**Files:**
- Modify: `settings/kis-mcp.settings.json`
- Modify: `src/kis_mcp/config.py`
- Modify: `scripts/tunnel-state.ps1`
- Create: `scripts/windows-credential.ps1`
- Create: `scripts/set-tunnel-credential.ps1`
- Modify: `scripts/setup-tunnel.ps1`
- Modify: `scripts/start-chatgpt.ps1`
- Test: `tests/test_tunnel_scripts.py`
- Test: `tests/test_startup_scripts.py`
- Test: `tests/test_remote_runtime.py`

**Interfaces:**
- Consumes: canonical settings, Windows Credential Manager, tunnel-client CLI, local MCP initialize request, and tunnel `/readyz` endpoint.
- Produces: per-instance credential storage, transient owned-process credential injection, static profile generation by default, optional live validation, server-before-tunnel startup, precise readiness errors, and bounded observation cleanup.

- [x] Add failing script-contract tests requiring `-ValidateLiveEndpoint`, default omission of doctor, `KIS_MCP_ENDPOINT_NOT_READY`, quiet startup fields, and no profile-invalid classification for endpoint refusal.
- [x] Replace file and JSON secret storage with per-user Windows Credential Manager targets and transient child-process environment injection.
- [x] Validate the selected Windows credential before moving an existing active profile into backup.
- [x] Refactor setup so profile creation and static file checks always run, while doctor/live validation runs only when requested.
- [x] Add bounded MCP readiness polling and classify refusal/timeout as `KIS_MCP_ENDPOINT_NOT_READY`.
- [x] Capture tunnel setup, server, and tunnel diagnostics in local runtime logs while keeping the operator console bounded.
- [x] Reduce startup success output to kis-mcp-owned fields and write a versioned startup-state record containing diagnostic log paths.
- [x] Add `ObservationSeconds` for supervised bounded observation followed by normal owned-process cleanup.
- [x] Run focused script tests to green.

### Task 4: Ownership, measurement, documentation, and full verification

**Files:**
- Create: `docs/development/startup-hardening/ownership.md`
- Create: `docs/development/startup-hardening/slice-metrics.json`
- Modify: `SPEC.md`
- Modify: `docs/OPERATIONS.md`
- Modify: `docs/STARTUP-HARDENING.md`
- Update: `.work/changes/013-startup-hardening/tasks.md`
- Update: `.work/changes/013-startup-hardening/closeout.md`

- [x] Record the ownership handoff from closed change `007` to active change `013` without editing another active worktree.
- [x] Record the observed read set, edit set, and change-reason clusters for later MAS scoring.
- [x] Align documentation with the lifecycle-owned compatibility seam.
- [x] Rebase the branch linearly onto exact base `0915bfa67e4452240d2c5fef677670c0c68386c7`.
- [x] Run focused tests and `scripts/verify.ps1`.
- [x] Run supervised live setup/start observation with available identifiers without terminating unrelated listeners.
- [x] Run the final current-change scope check and `git diff --check` after closeout edits.
- [x] Review the complete diff for policy drift, seam leakage, secrets, and unrelated changes.
- [x] Prepare the verified tree for one amended linear commit; remote push and PR creation are reported separately after they occur.
