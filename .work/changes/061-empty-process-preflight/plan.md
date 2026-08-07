# Startup and Provider-Auth Lifecycle Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make selected-instance startup and GitHub runtime authentication operate as one deterministic lifecycle without false-green tests, throwaway GitHub processes, stale auth readiness, hidden device fallback, or shared human/machine deadlines.

**Architecture:** Keep the existing provider and capability boundaries. Harden PowerShell preflight locally; extend the provider-neutral persistent-client lifecycle with startup/runtime-tool state; suppress only pre-lifespan upstream discovery for persistent providers; keep existing aggregate discovery for other providers; make capability catalogue/readiness resolve current runtime provider evidence; and keep the launcher as the supervised owner of authentication timing/output. Do not hard-code GitHub's long-tail tool catalogue.

**Tech Stack:** PowerShell 7, Python 3.13, FastMCP 3.4.4, pytest, GitHub Windows Actions.

## Global Constraints

- Write only within `C:\Projects` at runtime.
- No unrestricted external network through Work.
- No permanent deletion; recovery remains quarantine-based.
- GitHub OAuth token remains process-memory state owned by the official provider process.
- PAT material is never forwarded to the GitHub MCP subprocess.
- Operation/development peer-instance isolation remains unchanged.
- Existing Supabase and Control Center discovery semantics remain unchanged.
- No static enumeration of the complete GitHub MCP tool surface.

---

### Task 1: Empty-process preflight and honest test harness

**Files:** `tests/test_startup_scripts.py`, `scripts/startup-instance-lifecycle.ps1`

- [x] Run startup helper expressions with `$ErrorActionPreference='Stop'`.
- [x] Retain the empty-array regression that exposes the original binder failure under terminating semantics.
- [x] Add `[AllowEmptyCollection()]` to the process collection parameter only; keep root-selection logic unchanged.
- [ ] Execute focused startup tests on Windows.

### Task 2: One GitHub process and runtime tool publication

**Files:** `tests/providers/test_client_runtime.py`, `tests/providers/github/test_server.py`, `src/kis_mcp/providers/client_runtime.py`, `src/kis_mcp/providers/contracts.py`, `src/kis_mcp/providers/github/server.py`

- [x] Add provider-neutral startup phase and runtime-tool snapshot state.
- [x] Require pre-lifespan persistent-provider listing to return no upstream components and make no client connection.
- [x] Run `get_me` and initial upstream tool discovery inside one outer client lifespan.
- [x] Share GitHub runtime state between builder, readiness probe, health, and runtime-tool probe.
- [x] Preserve the existing `ProviderDescriptor` positional contract by appending the optional runtime-tool probe after existing fields.
- [ ] Execute focused provider lifecycle/GitHub tests.

### Task 3: No disposable GitHub discovery and current capability readiness

**Files:** `src/kis_mcp/gateway/composition.py`, `src/kis_mcp/providers/platform.py`, `src/kis_mcp/capabilities/runtime.py`, `tests/providers/test_runtime_tool_surface.py`, `tests/capabilities/test_runtime_refresh.py`

- [x] Preserve aggregate mounted-provider component listing after composition; rely on persistent GitHub pre-lifespan suppression so Supabase/Control Center discovery is not regressed.
- [x] Add namespaced provider runtime-tool snapshots without mutating upstream tool objects.
- [x] Build the effective capability catalogue from immutable base contributions plus the captured static runtime surface and current provider runtime-tool snapshots.
- [x] Re-evaluate readiness/current catalogue for discovery, recommendation, eligibility, and dispatch instead of freezing authentication state at construction.
- [x] Keep the direct exposure plan fixed so newly discovered long-tail tools remain discoverable rather than automatically direct.
- [ ] Execute focused capability/platform tests.

### Task 4: Supervised OAuth timing and live retained stderr

**Files:** `tests/test_startup_scripts.py`, `scripts/start-chatgpt.ps1`, `docs/OPERATIONS.md`

- [x] Add a distinct `AuthenticationTimeoutSeconds` budget and validation.
- [x] Create the tunnel deadline only after server/OAuth readiness succeeds.
- [x] Replace deferred-only stream reads with incremental event-backed draining into retained logs.
- [x] Echo only server stderr live so OAuth/device-code guidance is visible without adding tunnel noise.
- [x] Reconcile operations documentation with the new lifecycle.
- [ ] Execute focused startup tests and one supervised live commissioning run.

### Task 5: Integrated review and verification

**Files:** all changed files plus `.work/changes/061-empty-process-preflight/{tasks.md,closeout.md}`

- [x] Review the complete implementation against the four original findings, HR-001..HR-003, provider compatibility, and simplicity/modularity boundaries; correct the initial Task 3 design so non-GitHub provider discovery remains intact.
- [ ] Run `pwsh -NoProfile -File .\scripts\change-workflow.ps1 check` from the governed worktree.
- [ ] Run the focused pytest set on Windows.
- [ ] Run `pwsh -NoProfile -File .\scripts\verify.ps1` on the exact final head.
- [ ] Obtain Windows CI evidence for the exact final head when a dispatcher/runner is available.
- [ ] Record executable evidence in `closeout.md`, move `scope.json` to `ready`, make PR #76 ready, and merge only after all required gates pass.
