# Provider Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a provider-neutral module foundation that houses GitHub, Supabase, and future MCP adapters behind stable contracts, deterministic registration, catalogue projection, and readiness aggregation.

**Architecture:** Keep common lifecycle and discovery behavior in focused files beneath `kis_mcp.providers`. Keep connector transport, authentication, settings, and server construction inside adapter packages. The common module imports no connector package and performs no network access.

**Tech Stack:** Python 3.11, immutable dataclasses, `StrEnum`, standard-library typing, JSON Schema, pytest.

## Global Constraints

- Preserve exactly HR-001, HR-002, and HR-003 as the Work enforcement decision set.
- Write only inside `C:\Projects` and never permanently delete artifacts.
- Add no dependencies, credentials, provider activation, installer, or network operation.
- Do not edit active paths owned by changes 005, 008, or 009.
- Keep provider-specific schemas and transports behind adapter packages.

---

### Task 1: Provider-neutral contracts

**Files:**
- Create: `src/kis_mcp/providers/contracts.py`
- Create: `src/kis_mcp/providers/__init__.py`
- Create: `tests/providers/test_provider_module.py`

**Interfaces:**
- Produces: `ProviderKind`, `ProviderBoundary`, `ProviderState`, `ProviderCapability`, `ProviderReadiness`, `ProviderDescriptor`, `ProviderBuilder`, and `ProviderReadinessProbe`.
- `ProviderDescriptor` validates non-empty identifiers and unique capability IDs.

- [ ] Write failing tests for descriptor validation, immutable JSON-safe projection, and duplicate capability rejection.
- [ ] Run the focused tests and confirm import or assertion failures.
- [ ] Implement the minimal immutable contracts and explicit package exports.
- [ ] Run the focused tests and confirm they pass.

### Task 2: Deterministic registry and catalogue

**Files:**
- Create: `src/kis_mcp/providers/registry.py`
- Create: `src/kis_mcp/providers/catalogue.py`
- Modify: `tests/providers/test_provider_module.py`

**Interfaces:**
- Consumes: `ProviderDescriptor`.
- Produces: `ProviderRegistry.register`, `ProviderRegistry.get`, `ProviderRegistry.list`, `ProviderRegistry.contains`, `ProviderCatalogue.entries`, and `ProviderCatalogue.find_by_capability`.

- [ ] Add failing tests for sorted registration, duplicate rejection, unknown lookup, and capability filtering without invoking builders.
- [ ] Run the focused tests and confirm failures.
- [ ] Implement deterministic registry storage and immutable catalogue projection.
- [ ] Run the focused tests and confirm they pass.

### Task 3: Readiness aggregation and service facade

**Files:**
- Create: `src/kis_mcp/providers/health.py`
- Create: `src/kis_mcp/providers/service.py`
- Modify: `tests/providers/test_provider_module.py`

**Interfaces:**
- Consumes: `ProviderRegistry`, `ProviderDescriptor`, and readiness probes.
- Produces: `ProviderHealthSummary`, `aggregate_provider_health`, and `ProviderService`.

- [ ] Add failing tests for ready, degraded, disabled, unavailable, and probe-failure aggregation.
- [ ] Add a failing architecture test proving the service does not call provider builders during listing or health aggregation.
- [ ] Implement bounded readiness aggregation and the thin facade.
- [ ] Run the focused tests and confirm they pass.

### Task 4: Versioned provider contract schema

**Files:**
- Create: `contracts/providers/module/provider-module.schema.json`
- Modify: `tests/providers/test_provider_module.py`

**Interfaces:**
- Produces: JSON Schema version 1 for descriptor, capability, readiness, catalogue entry, and health summary shapes.

- [ ] Add a failing test that loads and validates required schema identities and closed object shapes.
- [ ] Create the schema with `additionalProperties: false` for public records.
- [ ] Validate the JSON document and rerun focused tests.

### Task 5: Product architecture and modularity record

**Files:**
- Create: `docs/PROVIDER-MODULE-PRODUCT-SPEC.md`
- Create: `docs/development/provider-module/modularity-assessment.md`
- Create: `docs/development/provider-module/implementation-evidence.md`

**Interfaces:**
- Documents the approved platform diagram, Provider module structure, dependency direction, extension contract, connector migration path, non-goals, and measured/unmeasured modularity evidence.

- [ ] Write the product specification with the exact approved platform architecture diagram.
- [ ] Record the modularity assessment using `M`, `D`, and `U` evidence labels and `MAS = n/a` where inputs are unmeasured.
- [ ] Record implementation and verification evidence without claiming connector migration not performed in this slice.

### Task 6: Review, verification, and PR preparation

**Files:**
- Modify: `.work/changes/010-provider-module/tasks.md`
- Modify: `.work/changes/010-provider-module/closeout.md`
- Modify: `docs/development/provider-module/implementation-evidence.md`

**Interfaces:**
- Produces: reviewable branch and unmerged pull request.

- [ ] Run focused provider-module tests through the locked repository environment.
- [ ] Validate the JSON schema.
- [ ] Run change scope validation and record the known duplicate historical-claim defect if it remains.
- [ ] Run full repository verification.
- [ ] Run Git whitespace and final diff review.
- [ ] Apply the modularity-assessment self-audit and completion verification.
- [ ] Commit, push `change/010-provider-module`, create a non-draft reviewable PR, and do not merge it.
