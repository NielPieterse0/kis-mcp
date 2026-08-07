# Startup and Control Center Closeout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use Superpowers TDD while executing each behavior task on the existing 077 worktree.

**Goal:** Correct Control Center local commissioning status, restore configured stateless HTTP behavior, and make ordinary startup promptless without weakening tunnel credential storage.

**Architecture:** Keep the three fixes at their existing seams. Provider readiness owns semantic status, Control Center rendering owns presentation, `RuntimeConfig` owns transport settings, and startup scripts own process/credential handoff. Restore per-user Windows Credential Manager only for the tunnel runtime credential; leave the generic encrypted vault as an independent explicit-maintenance facility.

**Tech Stack:** Python 3.13, FastMCP 3.4.4, PowerShell 7, Windows Credential Manager, pytest.

## Global constraints

- Work only in `.work/worktrees/077-control-center-commissioning-status`.
- Stay inside `scope.json`; do not edit authority docs claimed by change 078.
- Add or change regression tests before production behavior.
- Never persist plaintext credentials in repository files, profiles, logs, runtime JSON, or argv.
- Preserve HR-001, HR-002, and HR-003 exactly.

---

### Task 1: Truthful local Control Center status

**Files:**
- Modify: `tests/providers/test_control_center_provider.py`
- Modify: `tests/control_center/test_control_center_render.py`
- Modify: `src/kis_mcp/providers/control_center/provider.py`
- Modify: `src/kis_mcp/control_center/render.py`

**Interfaces:**
- Consumes provider readiness `details.user_status` and `details.commissioning`.
- Produces a local-read-only status with no commissioning action and a concise UI rendering for all-`not_applicable` commissioning evidence.

- [x] Run the existing provider regression and add a render assertion that local-only commissioning does not display six `Not applicable` rows.
- [x] Confirm the render assertion fails before the UI change.
- [x] Filter all-`not_applicable` commissioning rows into one `Local provider — no commissioning required` badge/message.
- [x] Run the two focused Control Center test files and confirm they pass.

---

### Task 2: Honor stateless HTTP configuration

**Files:**
- Modify: `tests/test_remote_runtime.py`
- Modify: `src/kis_mcp/config.py`
- Modify: `src/kis_mcp/remote_runtime.py`

**Interfaces:**
- `RuntimeConfig.remote_stateless_http -> bool`
- `RuntimeConfig.remote_json_response -> bool`
- `run_remote_instance()` passes those values to `FastMCP.run`.

- [x] Change the remote-runtime test to expect `stateless_http=True` and settings-derived JSON response behavior.
- [x] Run `tests/test_remote_runtime.py::test_remote_runtime_uses_streamable_http_arguments` and confirm it fails against the current hard-coded `False`.
- [x] Add read-only `RuntimeConfig` properties for the validated remote transport flags and consume them in `run_remote_instance`.
- [x] Run `tests/test_remote_runtime.py` and the smoke-script source-contract test suite.

---

### Task 3: Separate startup from vault unlock

**Files:**
- Modify: `tests/test_startup_scripts.py`
- Modify: `tests/test_tunnel_scripts.py`
- Modify: `scripts/start-chatgpt.ps1`
- Modify: `scripts/start.ps1`
- Modify: `scripts/startup-instance-lifecycle.ps1`
- Modify: `scripts/setup-tunnel.ps1`
- Modify: `scripts/set-tunnel-credential.ps1`
- Modify: `scripts/windows-credential.ps1`

**Interfaces:**
- `Get-KisMcpTunnelCredentialTarget -Reference <canonical tunnel secret ref> -> kis-mcp/tunnel/<instance>`.
- `Set-KisMcpWindowsCredential` stores the operator-supplied tunnel value once.
- `Get-KisMcpWindowsCredential` retrieves it non-interactively for setup/startup.
- Selected server identity is `python -m kis_mcp.remote_runtime --instance <name>`.
- [x] Replace old startup tests that require vault unlock with assertions that normal startup contains no unlock prompt, secrets launcher, or secret-aware process handoff.
- [x] Update lifecycle tests to expect the direct remote-runtime command and confirm those tests fail first.
- [x] Add deterministic tunnel credential-target derivation and switch set/setup/start scripts back to the existing Windows Credential helper.
- [x] Launch the stdio server directly from `start.ps1` and the remote server directly from `start-chatgpt.ps1`; keep the tunnel secret only in the owned tunnel process environment.
- [x] Update selected-process matching to the direct remote-runtime command.
- [x] Run `tests/test_startup_scripts.py` and `tests/test_tunnel_scripts.py` and confirm they pass.

---

### Task 4: Documentation, review, and repository verification

**Files:**
- Modify: `docs/STARTUP-HARDENING.md`
- Modify: `docs/development/secrets/README.md`
- Modify: `.work/changes/077-control-center-commissioning-status/tasks.md`
- Modify: `.work/changes/077-control-center-commissioning-status/closeout.md`

- [x] Document promptless runtime startup, one-time tunnel credential storage, stateless HTTP, and the vault/runtime separation.
- [x] Record `SPEC.md` and `docs/OPERATIONS.md` as deferred integration because active change 078 owns them.
- [x] Run focused tests for Control Center, remote runtime, startup scripts, and tunnel scripts.
- [x] Run architecture/modularity checks applicable to changed module seams.
- [x] Run `pwsh -NoProfile -File .\scripts\change-workflow.ps1 check`.
- [x] Run `pwsh -NoProfile -File .\scripts\verify.ps1`.
- [x] Inspect the final diff and obtain an advisory code review; resolve all material findings.
- [ ] Commit and create/update the PR, wait for required checks, then use the PR-completion landing gate for the exact head SHA.
- [ ] After merge, run safe change-workflow cleanup from clean `main`.
