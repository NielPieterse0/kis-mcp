# Commissioning Refresh Implementation Plan

> **For agentic workers:** Execute this plan task-by-task in the isolated worktree. Use test-first changes, review each completed task against the specification, and preserve the declared scope.

**Goal:** Make GitHub and Supabase commissioning status actionable and non-failure-oriented while preserving truthful fault and live-verification reporting.

**Architecture:** Provider-specific readiness probes own fixed user-facing onboarding state and commissioning metadata. The shared runtime status forwards those bounded fields without inferring provider-specific requirements. Supabase builds a local health-only server until project and credential prerequisites permit upstream proxy creation, so onboarding does not become a provider build failure.

**Tech stack:** Python 3.11+, FastMCP 3.4.4, pytest 8.4.x, JSON-backed provider settings, PowerShell repository verification.

## Global constraints

- Stay inside `scope.json`; do not touch Discover or policy paths.
- Add each behavior assertion before production code and confirm the expected failure.
- Do not perform authentication, external network calls, provider upgrades, or secret persistence.
- Preserve separate registration, mount, readiness, authentication, upstream connection, tool discovery, and live-verification evidence.
- Keep provider outputs redacted and deterministic.

---

### Task 1: Define provider-owned onboarding states

**Requirements:** R2, R3, R5, R6

**Files:**
- Modify: `tests/providers/github/test_server.py`
- Modify: `tests/providers/supabase/test_supabase_server.py`
- Modify: `src/kis_mcp/providers/github/server.py`
- Modify: `src/kis_mcp/providers/supabase/server.py`

**Interfaces:**
- Produces `readiness.details.user_status` with `state`, `label`, and `required_action`.
- Produces `readiness.details.commissioning` with fixed states for installation, configuration, authentication, upstream connection, tool discovery, and live verification.

- [ ] Add GitHub assertions requiring `Ready — authentication required`, an explicit OAuth action, and commissioning states that do not claim authentication.
- [ ] Run the focused GitHub test and confirm failure against the current summary/details.
- [ ] Implement the smallest GitHub readiness metadata change.
- [ ] Run the focused GitHub test and confirm it passes.
- [ ] Add Supabase assertions for project-initialization-required, authentication-required, keyring failure, and PAT-conflict branches.
- [ ] Run the focused Supabase test and confirm failure against the current degraded/incomplete behavior.
- [ ] Implement provider-neutral Supabase state mapping and fixed onboarding metadata without changing OAuth transport.
- [ ] Run the focused Supabase test and confirm it passes.

### Task 2: Keep Supabase mounted during project onboarding

**Requirements:** R1, R5, R6

**Files:**
- Modify: `tests/providers/supabase/test_supabase_server.py`
- Modify: `src/kis_mcp/providers/supabase/server.py`

**Interfaces:**
- `build_server(config, environment)` returns a local FastMCP server with `kis_supabase_health` when upstream preflight is incomplete.
- Upstream proxy construction remains unchanged when the provider-specific readiness record is fully ready.

- [ ] Add a failing test proving a missing project reference returns a health-only server and does not call `build_transport` or `create_proxy`.
- [ ] Confirm the test fails with `SUPABASE_PROJECT_SCOPE_REQUIRED` or an unexpected transport call.
- [ ] Build a plain local FastMCP server for incomplete preflight and retain the current proxy path for ready preflight.
- [ ] Run the complete Supabase provider test module and confirm it passes.

### Task 3: Preserve actionable status through the shared runtime

**Requirements:** R4, R5, R6

**Files:**
- Modify: `tests/providers/test_runtime_composition.py`
- Modify: `src/kis_mcp/providers/runtime.py`
- Modify: `src/kis_mcp/server.py`

**Interfaces:**
- `provider_runtime_status()` copies validated `user_status` and `commissioning` mappings from provider readiness details.
- Providers without those mappings retain the existing six-field `not_verified` fallback.

- [ ] Add a failing runtime-status test requiring provider-owned `user_status` and commissioning metadata to survive composition.
- [ ] Add fallback assertions for descriptors that do not publish the new metadata.
- [ ] Run the focused runtime composition test and confirm the provider-owned values are currently overwritten or absent.
- [ ] Implement bounded mapping extraction with a fixed fallback and no provider-ID branching.
- [ ] Update the `kis_provider_status` tool description to mention actionable next steps.
- [ ] Run the focused runtime composition tests and confirm they pass.

### Task 4: Align authoritative and user guidance

**Requirements:** R7, R8

**Files:**
- Modify: `SPEC.md`
- Modify: `docs/OPERATIONS.md`
- Modify: `docs/development/github-mcp-provider/README.md`
- Modify: `docs/development/supabase-mcp-provider/README.md`

- [ ] Update existing provider-status documentation to define the two ready/action-required states.
- [ ] State that missing Supabase project scope is onboarding, not provider degradation, while genuine local faults remain degraded/unavailable.
- [ ] State that GitHub executable/configuration readiness precedes OAuth authentication and live verification.
- [ ] Confirm documentation does not claim authenticated or upstream-verified operation and does not store project references or credentials.

### Task 5: Review, verify, and close

**Requirements:** R1-R8

**Files:**
- Modify: `.work/changes/026-commissioning-refresh/tasks.md`
- Modify: `.work/changes/026-commissioning-refresh/closeout.md`

- [ ] Review the final diff against the specification, MCP tool-design guidance, redaction requirements, and scope exclusions.
- [ ] Run focused provider tests with the worktree `PYTHONPATH` and the locked interpreter without synchronizing the shared environment.
- [ ] Run `pwsh -NoProfile -File .\scripts\change-workflow.ps1 check` from the change worktree.
- [ ] Run `git diff --check`.
- [ ] Serialize and run `pwsh -NoProfile -File .\scripts\verify.ps1` from the change worktree.
- [ ] Record requirement-to-evidence mapping, review result, recovery, residual risk, and exact verification outcomes in `closeout.md`.
