# Control Center UI Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Mount the KIS Control Center through the primary provider runtime and provide a complete, truthful, read-only operational dashboard.

**Architecture:** Keep the existing Control Center package as the UI and snapshot boundary. Add a bounded process-local observability registry populated by existing middleware/resolver hooks, enrich snapshots from local authority sources, and register the Control Center as a `LOCAL_READ_ONLY` provider enabled in provider runtime JSON. Avoid `server.py` and all Desktop Commander assets.

**Tech Stack:** Python 3.13, FastMCP 3.4.4, MCP Apps HTML resource contract, standard-library dataclasses/JSON/HTML/regex/threading, existing Discover and Provider services, pytest 8.4, PowerShell repository verification.

## Global Constraints

- Stay inside `.work/changes/043-control-center-ui-integration/scope.json`.
- Use TDD for every behavior change.
- Add no dependencies and perform no network access during runtime collection.
- Do not modify Desktop Commander, `server.py`, startup scripts, primary runtime settings, policy, `SPEC.md`, `docs/OPERATIONS.md`, or the approval register.
- Retain no raw tool argument values or result bodies in observability records.
- Keep the Control Center read-only; operational actions remain ordinary gateway tools.

---

### Task 1: Register and validate the isolated slice

**Files:**
- Create: `.work/changes/043-control-center-ui-integration/scope.json`
- Create: `.work/changes/043-control-center-ui-integration/spec.md`
- Create: `.work/changes/043-control-center-ui-integration/plan.md`
- Create: `.work/changes/043-control-center-ui-integration/tasks.md`
- Create: `.work/changes/043-control-center-ui-integration/closeout.md`

**Interfaces:**
- Produces: validated exclusive path claims for all later tasks.

- [ ] Run `pwsh -NoProfile -File scripts/change-workflow.ps1 validate` from the worktree.
- [ ] Run the focused existing Control Center suite as the baseline.
- [ ] Record the governance-wrapper command-bridge failure and emergency native-worktree registration in `closeout.md`.
- [ ] Commit governance artifacts before production changes.

### Task 2: Add bounded process-local observability

**Files:**
- Create: `src/kis_mcp/runtime_observability.py`
- Modify: `src/kis_mcp/middleware.py`
- Modify: `src/kis_mcp/desktop_commander.py`
- Modify: `src/kis_mcp/process_state.py`
- Test: `tests/test_runtime_observability.py`
- Test: `tests/test_middleware.py`
- Test: `tests/test_desktop_commander.py`
- Test: `tests/test_process_state.py`

**Interfaces:**
- Produces: `RuntimeObservability`, `RuntimeObservabilitySnapshot`, `get_runtime_observability()`, and `reset_runtime_observability_for_tests()`.
- Records: bounded recent calls and policy decisions; active process/search lifecycle; argument key names only.

- [ ] Write failing tests proving bounded ordering, redacted argument-key storage, policy-decision recording, process start/stop tracking, and search start/stop tracking.
- [ ] Run the focused tests and confirm failures because the registry/hooks do not exist.
- [ ] Implement immutable record contracts and a thread-safe bounded singleton registry.
- [ ] Record every middleware decision before allow/block/quarantine completion; record outcome without raw payloads.
- [ ] Extend the Desktop Commander success observer to update process/search lifecycle from known provider tool names and bounded identifiers.
- [ ] Run focused observability, middleware, resolver, and process-state tests until green.
- [ ] Commit the observability task.

### Task 3: Capture real provider composition and enriched local evidence

**Files:**
- Modify: `src/kis_mcp/providers/runtime.py`
- Modify: `src/kis_mcp/control_center/contracts.py`
- Modify: `src/kis_mcp/control_center/settings.py`
- Modify: `src/kis_mcp/control_center/snapshot.py`
- Modify: `settings/control-center.settings.json`
- Modify: `contracts/control-center/settings.schema.json`
- Test: `tests/providers/test_runtime_composition.py`
- Test: `tests/control_center/test_control_center_settings.py`
- Test: `tests/control_center/test_control_center_snapshot.py`
- Test: `tests/control_center/test_control_center_snapshot_limits.py`

**Interfaces:**
- Produces: `latest_provider_runtime_composition()` returning the current process composition snapshot.
- Extends `ControlCenterSnapshot` with approvals, Discover, provider runtime, observability, quarantine records/actions, and verification evidence.

- [ ] Write failing tests proving provider composition is published only after composition completes and is returned as an immutable snapshot.
- [ ] Write failing settings/schema tests for `approval_register_path`, section limits, and Discover enablement.
- [ ] Write failing snapshot tests for pending approval parsing, bounded Discover summary, provider mount/readiness truthfulness, observability projection, quarantine record projection, and isolated section degradation.
- [ ] Implement provider-composition publication without changing `server.py`.
- [ ] Extend settings and schema with strict fields and numeric bounds.
- [ ] Implement local evidence collectors using existing Discover/config/provider/quarantine services and explicit per-section diagnostics.
- [ ] Run focused runtime and snapshot tests until green.
- [ ] Commit the evidence task.

### Task 4: Build the complete host-themed dashboard

**Files:**
- Modify: `src/kis_mcp/control_center/render.py`
- Modify: `src/kis_mcp/control_center/app.py`
- Test: `tests/control_center/conftest.py`
- Test: `tests/control_center/test_control_center_render.py`
- Test: `tests/control_center/test_control_center_app.py`

**Interfaces:**
- Consumes: enriched `ControlCenterSnapshot`.
- Produces: deterministic self-contained HTML and structured fallback content.

- [ ] Write failing renderer tests for all required sections, responsive navigation, semantic headings, accessible status labels, host theme variables, hostile-text escaping, and no external resources.
- [ ] Write failing app tests proving each tool/resource read collects a fresh snapshot and preserves MCP App metadata.
- [ ] Refactor renderer into focused section helpers rather than extending one monolithic template.
- [ ] Implement overview, project/Discover, policy/approvals, providers, processes/searches, recent calls, quarantine, verification, and diagnostics sections.
- [ ] Show action tool names and status guidance without directly executing mutations.
- [ ] Run focused renderer and app tests until green.
- [ ] Commit the UI task.

### Task 5: Register Control Center as a mounted local provider

**Files:**
- Create: `src/kis_mcp/providers/control_center/__init__.py`
- Create: `src/kis_mcp/providers/control_center/provider.py`
- Modify: `src/kis_mcp/providers/platform.py`
- Modify: `src/kis_mcp/providers/__init__.py`
- Modify: `settings/providers/platform-runtime.provider.json`
- Create: `tests/providers/test_control_center_provider.py`
- Modify: `tests/providers/test_platform_composition.py`
- Test: `tests/control_center/test_gateway_integration.py`

**Interfaces:**
- Produces: `register_control_center_provider(registry)` and a `control-center` descriptor with `LOCAL_READ_ONLY` boundary.
- Gateway exposure: namespace `controlcenter`, model-visible `controlcenter_open_kis_control_center`, and `ui://controlcenter/kis-mcp/control-center.html`.

- [ ] Write failing descriptor/readiness tests for provider identity, boundary, capabilities, and builder output.
- [ ] Write failing platform registry/runtime JSON tests expecting `control-center` registration and enablement.
- [ ] Write a failing FastMCP integration test that composes the provider runtime and lists the namespaced entry tool and UI resource without launching a second process.
- [ ] Implement the provider descriptor and register it in the platform registry.
- [x] Enable it in provider runtime JSON under namespace `controlcenter`.
- [ ] Run provider and gateway-integration tests until green.
- [ ] Commit the provider-integration task.

### Task 6: Documentation, review, verification, PR, merge, and cleanup

**Files:**
- Modify: `docs/development/control-center/README.md`
- Modify: `.work/changes/043-control-center-ui-integration/tasks.md`
- Modify: `.work/changes/043-control-center-ui-integration/closeout.md`
- Modify: `.work/changes/043-control-center-ui-integration/scope.json`

**Interfaces:**
- Produces: operator instructions and exact verification/merge evidence.

- [ ] Document that the normal kis-mcp connector exposes the Control Center and that the standalone command is optional diagnostic mode, not a UI launcher.
- [ ] Review the exact diff against the specification, trust model, scope, and secret-safety requirements.
- [ ] Run focused suites for Control Center, providers, observability, middleware, resolver, and process state.
- [ ] Run `pwsh -NoProfile -File scripts/change-workflow.ps1 check`.
- [ ] Run `git diff --check`.
- [ ] Run `pwsh -NoProfile -File scripts/verify.ps1` on the final integrated head.
- [ ] Update status/evidence in change artifacts and commit the final closeout.
- [ ] Fetch and integrate current `origin/main`, rerun full verification, push the branch, open the PR, inspect exact remote files/reviews/checks, and merge without admin override.
- [ ] Fast-forward local `main`, run `change-workflow cleanup 043-control-center-ui-integration`, remove the remote branch, and prune only stale worktree metadata.
