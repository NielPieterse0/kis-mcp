# Dual Instance Commissioning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use test-driven development for behavior changes, review each task against `spec.md`, and use verification-before-completion before closeout.

**Goal:** Run `kis-op` and `kis-dev` concurrently through one launcher with exact app/instance/port identity enforcement.

**Architecture:** Keep `operation` and `development` as canonical internal keys. Add JSON `app_name` metadata and centralize selector normalization plus canonical app/port validation in `scripts/tunnel-state.ps1`. Keep `scripts/start-chatgpt.ps1` as the sole launcher, remove only the peer-listener rejection, retain selected-port exclusivity, and emit explicit identity evidence.

**Tech stack:** PowerShell 7, JSON configuration, Python/pytest structural and subprocess tests, FastMCP remote runtime, OpenAI tunnel client, Git change governance.

## Global constraints

- Work only inside the paths claimed by `scope.json`.
- Preserve HR-001, HR-002, and HR-003 unchanged.
- Do not stop, restart, or mutate the running `kis-op` process during implementation.
- Do not change tunnel IDs, secret references, provider exposure, or automatic failover behavior.
- Use LF line endings and the canonical external Python environment through repository scripts.
- Add failing tests before each behavior change.

---

### Task 1: Specify canonical app identity and selector behavior

**Files:**
- Modify: `settings/kis-mcp.settings.json`
- Modify: `scripts/tunnel-state.ps1`
- Test: `tests/test_tunnel_scripts.py`

**Interfaces:**
- Consumes: `settings.remote_mcp.instances` records.
- Produces: `Resolve-KisMcpInstanceName([string]$Instance) -> string` and `Get-KisMcpRemoteInstance(...)` results containing `name`, `app_name`, `port`, and `endpoint_url`.

- [ ] Add failing tests asserting JSON maps `operation` to `kis-op`/`8010` and `development` to `kis-dev`/`8011`.
- [ ] Add failing PowerShell subprocess tests for selectors `kis-op`, `op`, `operation`, `kis-dev`, `dev`, and `development`.
- [ ] Add failing tests for swapped app names, changed ports, and duplicate ports by loading temporary settings through a testable validation function or exact script contract.
- [ ] Run the focused tests and record the expected failures against the current implementation.
- [ ] Add `app_name` to both JSON records.
- [ ] Implement centralized selector normalization and exact canonical app/port validation.
- [ ] Return `app_name` from `Get-KisMcpRemoteInstance` and keep default selection through `active_instance`.
- [ ] Run focused tests and confirm they pass.

### Task 2: Permit concurrent launch while retaining own-port hardening

**Files:**
- Modify: `scripts/start-chatgpt.ps1`
- Test: `tests/test_startup_scripts.py`
- Test: `tests/test_tunnel_scripts.py`

**Interfaces:**
- Consumes: the normalized remote instance object from Task 1.
- Produces: one launcher accepting preferred app selectors and emitting deterministic startup identity.

- [ ] Replace the existing test that requires `KIS_MCP_OTHER_INSTANCE_ACTIVE` with a failing regression test that forbids peer-instance rejection.
- [ ] Add failing tests that require selected-port preflight before vault unlock and require the error to include app name and endpoint.
- [ ] Add failing tests that require startup output/state fields `app`, `instance`, and the exact endpoint.
- [ ] Run focused tests and record the expected failures.
- [ ] Remove only the peer-listener lookup and `KIS_MCP_OTHER_INSTANCE_ACTIVE` block.
- [ ] Keep the selected instance's `Get-NetTCPConnection` check and strengthen its diagnostic with app, instance, and endpoint.
- [ ] Emit app and canonical instance in console readiness output and startup-state JSON.
- [ ] Confirm process ownership and cleanup remain limited to the server and tunnel created by that launcher invocation.
- [ ] Run focused tests and confirm they pass.

### Task 3: Align specification and operator startup instructions

**Files:**
- Modify: `SPEC.md`
- Modify: `docs/OPERATIONS.md`
- Test: `tests/test_startup_scripts.py`

**Interfaces:**
- Consumes: implemented selectors and startup fields.
- Produces: one documented command pattern for both ChatGPT tools.

- [ ] Add failing documentation assertions requiring `kis-op`, `kis-dev`, ports `8010`/`8011`, and concurrent operation wording.
- [ ] Update `SPEC.md` to name the external apps and exact port mapping while preserving internal instance keys.
- [ ] Replace switch-over instructions and `KIS_MCP_OTHER_INSTANCE_ACTIVE` troubleshooting text in `docs/OPERATIONS.md`.
- [ ] Document the lean commands `pwsh -File .\scripts\start-chatgpt.ps1 kis-op` and `pwsh -File .\scripts\start-chatgpt.ps1 kis-dev` plus canonical-name compatibility.
- [ ] State that each launcher owns only its own server/tunnel pair and that no automatic failover occurs.
- [ ] Run focused tests and confirm they pass.

### Task 4: Verify and commission both instances

**Files:**
- Update: `.work/changes/041-dual-instance-commissioning/tasks.md`
- Update: `.work/changes/041-dual-instance-commissioning/closeout.md`

**Interfaces:**
- Consumes: completed code, tests, and documentation.
- Produces: current verification and live commissioning evidence.

- [ ] Run `pwsh -NoProfile -File scripts/change-workflow.ps1 check`.
- [ ] Run focused startup/tunnel tests through an approved repository command.
- [ ] Run `pwsh -NoProfile -File scripts/verify.ps1`.
- [ ] Confirm the existing `kis-op` health before development startup.
- [ ] Start `kis-dev` with bounded observation using the new selector while `kis-op` remains listening.
- [ ] Confirm `kis-op` remains healthy, `kis-dev` reports ready, and listeners are present only on their canonical ports.
- [ ] Stop only the bounded `kis-dev` commissioning processes after observation; do not touch `kis-op`.
- [ ] Review the final diff for scope, correctness, secrets, rollback, and unnecessary complexity.
- [ ] Record exact evidence and residual risks in `closeout.md`.
- [ ] Commit, push, create the PR, and use the PR Completion watcher until the exact head is ready or blocked.
- [ ] Request explicit landing approval for the exact ready head before merge-state mutation.
