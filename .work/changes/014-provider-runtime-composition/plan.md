# Provider Runtime Composition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mount configured GitHub and Supabase FastMCP adapters into the shared `kis-mcp` runtime under deterministic namespaces while containing uncommissioned-provider failures and exposing truthful runtime status.

**Architecture:** A strict provider-runtime settings loader validates the two approved external providers. A provider-neutral runtime composer asks `ProviderService` to build enabled adapters, validates each result as `FastMCP`, mounts it under a unique namespace, and records a redacted immutable result. `build_server()` invokes this composer after creating the existing Desktop Commander root server and exposes a status tool that combines mount results with fresh provider-neutral readiness.

**Tech Stack:** Python 3.11+, FastMCP 3.4.4, pytest 8.4.x, JSON/JSON Schema, PowerShell verification.

## Global Constraints

- Exactly HR-001, HR-002, and HR-003 remain the Work policy decision set.
- Do not edit GitHub or Supabase adapter internals, authentication, settings, installers, or smoke scripts.
- Do not edit startup-hardening, tunnel, remote-runtime, Desktop Commander resolver, middleware, policy, or quarantine files.
- Credentials and secret values must not enter repository JSON, logs, status records, or exceptions.
- External provider tools must be namespaced and additive.
- Missing or uncommissioned external providers must not prevent the core server from starting.
- Final shared `server.py` integration must preserve the active Skills slice and be reconciled after dependency integration.

---

### Task 1: Runtime Settings Contract

**Requirements:** R1, R8

**Files:**
- Create: `settings/providers/platform-runtime.provider.json`
- Create: `contracts/providers/runtime/platform-runtime.schema.json`
- Create: `src/kis_mcp/providers/runtime_settings.py`
- Create/Test: `tests/providers/test_runtime_composition.py`

**Interfaces:**
- Produces: `ProviderMountSetting(provider_id: str, enabled: bool, namespace: str)`
- Produces: `ProviderRuntimeSettings(schema_version: int, providers: tuple[ProviderMountSetting, ...])`
- Produces: `load_provider_runtime_settings(repository_root: Path | None = None) -> ProviderRuntimeSettings`

- [ ] Write tests proving the canonical JSON loads as exactly `github-mcp` and `supabase`, ordered by provider ID, with namespaces `github` and `supabase`.
- [ ] Write tests proving unknown top-level keys, unknown provider IDs, duplicate IDs, duplicate namespaces, invalid namespaces, missing required keys, and non-boolean `enabled` values fail with `ProviderRuntimeSettingsError`.
- [ ] Run the focused tests and preserve the expected import/configuration failures.
- [ ] Implement frozen dataclasses, exact-key validation, approved-ID validation, namespace regex validation, deterministic ordering, and the canonical settings loader.
- [ ] Add a closed JSON Schema mirroring the loader and validate the canonical JSON against it in tests.
- [ ] Run focused settings tests to green.

### Task 2: Provider-Neutral Runtime Composer

**Requirements:** R2, R3, R4, R5, R6

**Files:**
- Create: `src/kis_mcp/providers/runtime.py`
- Modify/Test: `tests/providers/test_runtime_composition.py`

**Interfaces:**
- Consumes: `ProviderService.build(provider_id)`, `ProviderService.health()`, `ProviderRuntimeSettings`
- Produces: `ProviderMountState` enum values `disabled`, `build_failed`, `invalid_builder_result`, `mounted`
- Produces: `ProviderMountResult` with `provider_id`, `namespace`, `enabled`, `build_attempted`, `built`, `mounted`, `state`, and optional `error_type`
- Produces: `ProviderRuntimeComposition(results: tuple[ProviderMountResult, ...])`
- Produces: `compose_provider_runtime(server: FastMCP, service: ProviderService, settings: ProviderRuntimeSettings) -> ProviderRuntimeComposition`
- Produces: `provider_runtime_status(service: ProviderService, composition: ProviderRuntimeComposition) -> dict[str, object]`

- [ ] Write a fake FastMCP provider with one tool and a fake `ProviderService` fixture.
- [ ] Write a failing test proving disabled providers are not built and return `disabled` state.
- [ ] Write a failing test proving enabled providers build in stable provider-ID order, mount under configured namespaces, and expose namespaced tools.
- [ ] Write failing tests proving builder exceptions are contained with exception type only and invalid non-FastMCP builder results are contained.
- [ ] Write a failing test proving duplicate/unknown runtime selection cannot reach composition.
- [ ] Write a failing test proving status combines mount results with current provider-neutral readiness without claiming authentication, connection, discovery, or live verification.
- [ ] Implement immutable mount records, deterministic composition, FastMCP type validation, namespaced `server.mount`, and redacted exception containment.
- [ ] Implement the versioned status projection and run focused composer tests to green.

### Task 3: Shared Server Integration and Public Status Tool

**Requirements:** R3, R4, R5, R6, R7

**Files:**
- Modify: `src/kis_mcp/server.py`
- Modify/Test: `tests/providers/test_runtime_composition.py`
- Modify/Test: `tests/test_public_contracts.py`

**Interfaces:**
- `build_server(config=None, *, validate_provider=True, provider_service=None, provider_runtime_settings=None) -> FastMCP`
- Public tool: `kis_provider_status() -> dict[str, object]`

- [ ] Write a failing integration test that injects a fake service/runtime settings into `build_server(validate_provider=False)` and proves a fake external tool appears as `github_echo` while existing gateway tools remain present.
- [ ] Write a failing integration test that injects builders which raise and proves `build_server()` still succeeds and `kis_provider_status` reports redacted failure states.
- [ ] Write a public-contract test requiring `kis_provider_status` alongside the existing gateway and Discover tools.
- [ ] Modify `server.py` to build the default platform service and load runtime settings only when injections are absent.
- [ ] Compose external providers after the root proxy and local module registrations are created, then register `kis_provider_status` over the retained composition and service.
- [ ] Preserve the existing middleware registration and prove namespaced fake provider calls remain callable.
- [ ] Run the focused runtime, public-contract, middleware, and server tests to green.

### Task 4: Current-State Documentation

**Requirements:** R8

**Files:**
- Modify: `SPEC.md`
- Modify: `docs/OPERATIONS.md`
- Create: `docs/development/provider-runtime-composition/verification.md`

**Interfaces:**
- Documents the canonical runtime settings path, namespace behavior, failure containment, status semantics, and remaining OAuth commissioning work.

- [ ] Update `SPEC.md` current implementation and public interface sections to include provider runtime composition and `kis_provider_status` without claiming authenticated provider operation.
- [ ] Update `docs/OPERATIONS.md` with configuration/status interpretation and precise uncommissioned-provider behavior; do not add PAT or OAuth instructions in this slice.
- [ ] Record focused test, full verification, scope, and residual commissioning evidence in the development verification document.
- [ ] Search authority docs for stale claims that providers are only registered or that the runtime has only one provider path; correct only current-state claims in shared owned documentation.

### Task 5: Review, Verification, and Delivery

**Requirements:** R1-R8

**Files:**
- Modify: `.work/changes/014-provider-runtime-composition/tasks.md`
- Modify: `.work/changes/014-provider-runtime-composition/closeout.md`
- Review: all changed files

**Interfaces:**
- Produces current verification and rollback evidence for the exact branch head.

- [ ] Run the repository code-review workflow against specification, plan, diff, tests, security, failure containment, and dependency boundaries.
- [ ] Fix all blocking findings and rerun affected focused tests.
- [ ] Run `pwsh -NoProfile -File .\scripts\change-workflow.ps1 check`; record any pre-existing duplicate-claim limitation separately from bounded changed-path evidence.
- [ ] Run `pwsh -NoProfile -File .\scripts\verify.ps1` from the worktree.
- [ ] Run `git diff --check` and inspect final `git status`.
- [ ] Complete `tasks.md` and `closeout.md` with requirement-to-evidence mapping, exact commands/results, rollback, skipped live checks, and residual OAuth commissioning.
- [ ] Commit and push the exact verified branch, then open a draft pull request that declares dependency on the Skills slice and excludes OAuth commissioning.

## Integration Sequence and Checkpoints

1. Settings loader and schema pass independently.
2. Runtime composer passes against fake providers without touching the shared server.
3. Shared server integration passes with injected fake providers and failure cases.
4. Documentation matches verified behavior.
5. Full repository verification and review pass on the exact final diff.
6. Draft PR remains blocked on final integration with `012-skills-module` and later OAuth slices.

## Migration, Rollout, Observability, and Rollback

- No data migration.
- Canonical defaults enable GitHub and Supabase composition attempts under `github` and `supabase`; unavailable builders remain visible but do not stop the core runtime.
- Operators can temporarily disable an external provider through the runtime JSON and restart the server.
- `kis_provider_status` is the runtime observation surface; it must distinguish mounted from ready and must not claim live verification.
- Roll back by reverting the change commit or disabling both provider entries. Preserve all generated provider state and credentials.

## Security and Data-Handling Checks

- Verify no raw builder exception message is returned.
- Verify no environment values or credentials are serialized.
- Verify namespaces are validated and unique.
- Verify adapters retain their own middleware after mounting.
- Verify Work policy files and middleware are unchanged.

## Documentation and Operational Updates

- Update only current-state `SPEC.md` and `docs/OPERATIONS.md` plus change evidence.
- Do not revise GitHub/Supabase authentication guidance until their dedicated OAuth slices.

## Plan Review Approval

Approved by the operator's accepted provider-module review and instruction to continue. Execution proceeds inline in this session.

## Completion and Stop Conditions

Stop when R1-R8 reconcile to current tests and documentation, the full repository verification is green, blocking review findings are resolved, the branch is committed/pushed, and remaining GitHub/Supabase OAuth commissioning is explicitly deferred.
