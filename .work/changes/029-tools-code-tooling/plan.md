# Tools Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a provider-neutral deterministic Tools kernel that later adapters can consume without owning generic framework files.

**Architecture:** Follow the existing Providers module shape while keeping independent Tool contracts. Immutable descriptors feed a deterministic registry, metadata catalogue, contained health aggregation, and thin construction service.

**Tech Stack:** Python 3.11 stdlib, pytest.

## Global Constraints

- Work only in `.work/worktrees/029-tools-code-tooling` on `change/029-tools-code-tooling`.
- Write only the exact paths in `scope.json`.
- Preserve exactly HR-001, HR-002, and HR-003.
- Do not implement adapters, settings, installers, network access, credentials, gateway integration, or public MCP operations.
- Do not touch Codex-specific paths owned by 035.

---

### Task 1: Tool contracts and registry

**Files:**
- Create: `src/kis_mcp/tools/contracts.py`
- Create: `src/kis_mcp/tools/registry.py`
- Test: `tests/tools/test_tool_module.py`

**Interfaces:**
- Produces: `ToolKind`, `ToolBoundary`, `ToolState`, `ToolCapability`, `ToolReadiness`, `ToolDescriptor`, `ToolRegistry`.

- [x] Write failing tests for JSON projection, typed validation, duplicate capabilities, stable registry ordering, duplicate IDs, and unknown IDs.
- [x] Run the focused tests and confirm collection/import failure.
- [x] Implement the minimal immutable contracts and registry.
- [x] Run the focused tests and confirm the Task 1 tests pass.
- [x] Commit the Task 1 files.

### Task 2: Catalogue, health, and service

**Files:**
- Create: `src/kis_mcp/tools/catalogue.py`
- Create: `src/kis_mcp/tools/health.py`
- Create: `src/kis_mcp/tools/service.py`
- Create: `src/kis_mcp/tools/__init__.py`
- Modify: `tests/tools/test_tool_module.py`

**Interfaces:**
- Consumes: the Task 1 descriptor and registry contracts.
- Produces: `ToolCatalogueEntry`, `ToolCatalogue`, `ToolHealthSummary`, `aggregate_tool_health`, `ToolService`.

- [x] Add failing tests proving catalogue/health do not build tools, disabled tools are not probed, failures are redacted, identity mismatches are contained, and explicit service build calls one builder.
- [x] Run focused tests and confirm the new failures.
- [x] Implement catalogue, health, service, and public exports.
- [x] Run all focused Tools tests and confirm pass.
- [x] Commit the Task 2 files.

### Task 3: Review, verification, and integration

- [x] Confirm the Tools module imports no provider, server, policy, network, credential, or adapter implementation.
- [x] Run `pwsh -NoProfile -File scripts/change-workflow.ps1 validate` and `check`; record any unrelated repository-governance blocker separately.
- [x] Run focused tests with the locked project interpreter.
- [x] Run `pwsh -NoProfile -File scripts/verify.ps1` serially.
- [x] Review the full diff against the specification and simplify unnecessary duplication.
- [ ] Commit, push, create and review the PR, merge the exact verified head, update local `main`, and clean the worktree without force.
- [ ] Rebase 035 onto the merged Tools foundation before resuming Codex integration.
