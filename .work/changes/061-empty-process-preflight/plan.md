# Startup and Provider-Auth Lifecycle Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make selected-instance startup and GitHub runtime authentication operate as one deterministic lifecycle without false-green tests, throwaway GitHub processes, stale auth readiness, hidden device fallback, or shared human/machine deadlines.

**Architecture:** Keep the existing provider and capability boundaries. Harden PowerShell preflight locally; extend the provider-neutral persistent-client lifecycle with startup/runtime-tool state; make capability catalogue/readiness resolve current runtime provider evidence; and keep the launcher as the supervised owner of authentication timing/output. Do not hard-code GitHub's long-tail tool catalogue.

**Tech Stack:** PowerShell 7, Python 3.13, FastMCP 3.4.4, pytest, GitHub Windows Actions.

## Global Constraints

- Write only within `C:\Projects` at runtime.
- No unrestricted external network through Work.
- No permanent deletion; recovery remains quarantine-based.
- GitHub OAuth token remains process-memory state owned by the official provider process.
- PAT material is never forwarded to the GitHub MCP subprocess.
- Operation/development peer-instance isolation remains unchanged.
- No static enumeration of the complete GitHub MCP tool surface.

---

### Task 1: Empty-process preflight and honest test harness

**Files:** `tests/test_startup_scripts.py`, `scripts/startup-instance-lifecycle.ps1`

**Interface:** `Get-KisMcpRootProcessIds -Processes <object[]>` accepts zero or more processes and returns zero or more root PIDs.

- [ ] Modify `_run_startup_lifecycle` so each expression runs after `$ErrorActionPreference='Stop'`.
- [ ] Add/retain an empty-array regression and run it on Windows; expected RED is the current `Cannot bind argument ... empty array` failure.
- [ ] Add `[AllowEmptyCollection()]` to the `Processes` parameter only; keep the root-selection algorithm unchanged.
- [ ] Re-run the focused startup tests; expected GREEN is zero stderr/binder errors and the existing root-selection behavior unchanged.

### Task 2: One GitHub process and runtime tool publication

**Files:** `tests/providers/test_client_runtime.py`, `tests/providers/github/test_server.py`, `src/kis_mcp/providers/client_runtime.py`, `src/kis_mcp/providers/contracts.py`, `src/kis_mcp/providers/github/server.py`

**Interfaces:**
- `ProviderStartupState.phase` records `idle|starting|ready|failed|stopped` plus optional error type.
- `ProviderRuntimeToolState.snapshot()` returns the latest immutable tuple of discovered FastMCP tool objects.
- `ProviderDescriptor.runtime_tools_probe` is optional and returns a sequence of runtime tool objects.
- `PersistentClientProxyProvider(..., startup_state=..., runtime_tools=...)` publishes startup and tool state from inside its lifespan.

- [ ] Write lifecycle tests requiring one connection while `get_me` and `list_tools` both run, a populated runtime-tool snapshot, and one disconnect only after lifespan exit.
- [ ] Write GitHub descriptor/server tests requiring shared state between builder/readiness and no PAT propagation.
- [ ] Run focused tests; expected RED is missing state/probe support.
- [ ] Implement the two provider-neutral state objects and update the persistent lifespan to `connect -> startup call -> list tools -> publish ready -> yield -> stop`.
- [ ] Wire GitHub registration/build/readiness to those shared objects and add the optional descriptor runtime-tool probe.
- [ ] Re-run focused tests to GREEN.

### Task 3: No construction-time GitHub discovery and current capability readiness

**Files:** `src/kis_mcp/gateway/composition.py`, `src/kis_mcp/providers/platform.py`, `src/kis_mcp/capabilities/runtime.py`, `src/kis_mcp/capabilities/resolver.py`, `src/kis_mcp/capabilities/tools.py`, `tests/providers/test_platform_composition.py`, `tests/capabilities/*`

**Interfaces:**
- Composition captures the core Desktop Commander runtime surface before external providers mount and local-provider tools without aggregating external mounts.
- `provider_runtime_tools(service, composition)` returns namespaced tool snapshots currently published by provider descriptors.
- `CapabilityRuntimeState` rebuilds the effective catalogue from immutable base contributions plus a runtime-tool source and evaluates current readiness when operations are searched/recommended/executed.

- [ ] Add tests proving external provider `list_tools` is not called during gateway construction and that publishing a runtime GitHub tool later makes it searchable/eligible without rebuilding the gateway.
- [ ] Add a test proving direct exposure does not automatically expand when a long-tail tool appears.
- [ ] Run focused tests; expected RED is construction-time provider enumeration and frozen readiness/catalogue state.
- [ ] Move aggregate core listing before external provider mount; list late local tools through `server.local_provider` only.
- [ ] Add provider runtime-tool namespacing and feed it into a dynamic capability runtime-tool source.
- [ ] Make capability search/resolver/execution evaluate the current catalogue/readiness rather than construction-time auth evidence.
- [ ] Re-run focused tests to GREEN.

### Task 4: Supervised OAuth timing and live retained stderr

**Files:** `tests/test_startup_scripts.py`, `scripts/start-chatgpt.ps1`, `docs/OPERATIONS.md`

**Interfaces:**
- `TimeoutSeconds` remains the machine/tunnel readiness timeout.
- `AuthenticationTimeoutSeconds` bounds server startup plus supervised OAuth independently.
- Owned process stderr can be drained incrementally to the existing log and optionally echoed live; shutdown performs a final drain and cleanup.

- [ ] Add tests requiring a distinct authentication deadline and a fresh tunnel deadline created only after `Wait-McpReady` succeeds.
- [ ] Add tests requiring live server-stderr draining while retaining the same server stderr log path.
- [ ] Run focused tests; expected RED is the single shared deadline/deferred-only stderr behavior.
- [ ] Implement separate deadline variables and validation.
- [ ] Replace deferred-only stderr handling with event/job-backed incremental draining; echo only server stderr, keep stdout/tunnel streams logged without extra console noise, and perform final drain/cleanup at shutdown.
- [ ] Update operations documentation to describe the two timeout phases and live OAuth/device fallback console behavior.
- [ ] Re-run startup tests to GREEN.

### Task 5: Integrated review and verification

**Files:** all changed files plus `.work/changes/061-empty-process-preflight/{tasks.md,closeout.md}`

- [ ] Run focused provider, capability, and startup tests.
- [ ] Run the canonical repository verification entry point on Windows.
- [ ] Review the complete branch diff against the four original findings, the approved spec, HR-001..HR-003, and simplicity/modularity boundaries.
- [ ] Fix only verified blocking findings and rerun affected checks.
- [ ] Record exact evidence in `closeout.md`, move `scope.json` to `ready` only when current evidence supports it, then create a PR rather than merging directly.
