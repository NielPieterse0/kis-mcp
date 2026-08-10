# Discover Serena Shared Client Lifecycle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development for the behavior change and superpowers:verification-before-completion before closeout.

**Goal:** Preserve Serena's active shared runtime client across nested FastMCP proxy contexts so Discover semantic enrichment can reuse the commissioned provider.

**Architecture:** Keep the existing persistent Serena/FastMCP client design. Add nesting ownership to `_SharedProviderClient`: publish the active client on first entry, retain it across nested exits, and clear only when the outermost context exits. Do not change Discover or provider contracts.

**Tech Stack:** Python 3.11, FastMCP 3.4.4, pytest 8.4.2, Serena 1.6.1, PowerShell repository verification.

## Global constraints

- Stay inside 089 declared paths.
- Preserve exactly HR-001 / HR-002 / HR-003.
- Keep Serena offline and project state beneath `C:\Projects\.kis-mcp\serena`.
- Do not alter direct Serena exposure or persistent Discover schemas.
- Write and observe the regression failing before production edits.

---

### Task 1: Reproduce nested shared-client lifecycle

**Files:**
- Test: `tests/providers/test_context7_serena_providers.py`

**Interfaces:**
- Consumes: `_SharedProviderClient.__aenter__`, `_SharedProviderClient.__aexit__`.
- Proves: nested exit must not clear `SerenaRuntimeAdapter._active_client` while outer context remains open.

- [ ] Add one async regression using a minimal re-entrant client stub.
- [ ] Assert active client/loop exist inside outer context, remain after nested exit, and clear after outer exit.
- [ ] Run only that test and confirm it fails because the nested exit clears active state.

### Task 2: Preserve outer lifecycle state

**Files:**
- Modify: `src/kis_mcp/providers/serena/adapter.py`
- Test: `tests/providers/test_context7_serena_providers.py`

**Interfaces:**
- Produces: reference-counted `_SharedProviderClient` context ownership with unchanged public adapter API.

- [ ] Add the minimum context-depth state to `_SharedProviderClient`.
- [ ] Publish the active client on entry and clear it only when the final active context exits.
- [ ] Run the regression and focused Serena/provider suite until green.

### Task 3: Verify and commission

**Files:**
- Update: `.work/changes/089-discover-serena-shared-client-lifecycle/{tasks,closeout}.md`

- [ ] Run `scripts/change-workflow.ps1 check`.
- [ ] Run canonical `scripts/verify.ps1` on the exact 089 head.
- [ ] Fast-forward into clean `main` only after green verification.
- [ ] Restart `kis-dev`; force a fresh Discover generation and confirm Serena semantic status is no longer independently failed.
- [ ] Re-run provider live smoke, Project preview, exact registered-GitHub verification, and clean-state audit.
- [ ] Publish exact verified `main`, close 089, and run governed cleanup without force deletion.
