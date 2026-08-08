# Project Registry Routing Implementation Plan

> Execute task-by-task in `change/078-project-registry-routing`; use TDD for behavioral changes and preserve active parallel claims.

**Goal:** Make KIS project-neutral across `C:\Projects` using one central registry, global GitHub/Supabase account authentication, and explicit per-operation resource coordinates.

**Architecture:** `kis_mcp.projects` owns strict project contracts/settings/lookup. Gateway composition loads one immutable registry and injects a registry-backed compatibility repository selector into existing provider composition. GitHub routing authorizes the registered union. Supabase uses one unscoped persistent OAuth client and middleware that validates explicit `project_id` values. Work Management overlays registry identity onto its existing behavior settings.

**Tech stack:** Python 3.11+, FastMCP 3.4.4, pytest 8.4.2, strict JSON/JSON Schema, PowerShell commissioning scripts, repository change-governance workflow.

## Global constraints

- Stay inside `scope.json`; validate any scope expansion before editing the added path.
- Do not touch active parallel claims or historical change records.
- Add/modify tests first, run them red, then make the smallest passing production change.
- Keep project refs/repository coordinates as non-secret routing values; store no OAuth/PAT/publishable key values.
- Preserve exact HR-001/HR-002/HR-003 behavior.
- Do not introduce mutable global active-project authorization state.
- Keep `projects` independent from Gateway, Providers, Work Management, and Discover.

---

### Task 1: Central project registry shared kernel

**Create:** `settings/projects.settings.json`, `contracts/projects/project-registry.schema.json`, `src/kis_mcp/projects/{__init__,contracts,settings,registry,platform}.py`, `tests/projects/**`.
- [x] Write failing strict-loader tests for valid KIS/GPT-OS entries, duplicate IDs/roots/provider resources, malformed refs, boundary escape, and unknown keys.
- [x] Write failing registry lookup/rendering tests and gateway project-tool registration tests.
- [x] Implement provider-neutral project contracts and GitHub coordinate normalization without importing provider modules.
- [x] Implement immutable registry lookup by project ID/root and provider resource indexes.
- [x] Implement strict checked-in settings loader and read-only project list/status tools plus a normalized capability contribution.
- [x] Seed `kis-mcp` with GitHub Project #1 and Supabase ref `mmxuicfrdalymczdapjq`; seed `gpt-os` with its local/GitHub repository identity only.
- [x] Run focused project tests green.

### Task 2: Repository compatibility and GitHub registered-union routing

**Modify:** `src/kis_mcp/repositories/settings.py`, `src/kis_mcp/providers/github/routing.py`, `src/kis_mcp/gateway/{context,composition}.py`.
**Test:** `tests/repositories/test_project_registry_settings.py`, `tests/providers/github/test_project_registry_routing.py`, `tests/gateway/test_project_context.py`.

- [x] Write failing tests showing a registry-backed selector resolves GPT-OS without a target-repo KIS file while legacy loader behavior remains available.
- [x] Write failing GitHub routing tests for two registered repos/Projects and negative unregistered coordinates.
- [x] Write failing gateway composition test proving the registry is instance-owned and injected into repository authorization.
- [x] Add the narrow registry-to-`RepositorySettings` compatibility adapter.
- [x] Change GitHub routing to use registered union properties when present, falling back to legacy single-repository behavior.
- [x] Wire registry loading/injection at the gateway composition root and retain it on `GatewayComposition`.
- [x] Add project capability contribution before exposure planning; add `kis_list_projects` and `kis_project_status` to the bounded direct profile.
- [x] Run focused repository/GitHub/gateway tests green.
### Task 3: Supabase global OAuth and registered project routing

**Modify:** `settings/providers/supabase-mcp.provider.json`, `contracts/providers/supabase/settings.schema.json`, `src/kis_mcp/providers/supabase/**`, `tests/providers/supabase/**`.

- [x] Rewrite Supabase tests first to require config schema v3 without `project_ref_env`, unscoped upstream URL, and readiness independent of project env.
- [x] Add failing persistent-client lifecycle tests for Supabase using the provider-neutral `PersistentClientProxyProvider` without a startup tool call.
- [x] Add failing routing middleware tests: registered `project_id` accepted; unregistered ID rejected; targetless read discovery accepted; targetless mutation rejected.
- [x] Remove project-ref environment handling from Supabase config/runtime and keep `read_only`/`features` as official endpoint query options.
- [x] Build the Supabase server over one persistent OAuth client for the parent provider lifespan and publish runtime tool snapshots.
- [x] Load the project registry as the provider routing allowlist and keep OAuth/account identity separate from project identifiers.
- [x] Update readiness/user-status/descriptor wording to global account OAuth with per-call project IDs.
- [x] Run all Supabase provider tests green.

### Task 4: Work-management compatibility bridge

**Modify:** `src/kis_mcp/work_management/settings.py`.
**Test:** `tests/work_management/test_project_registry_bindings.py`.

- [x] Write failing tests proving existing feature/gate/evidence behavior is preserved while managed project local/GitHub identity and matching GitHub Project coordinates come from the central registry.
- [x] Keep existing backend-binding IDs for compatibility with the active P5 slice; overlay only identity/coordinates that the registry owns.
- [x] Fail closed on conflicting registry/work-management identity instead of silently routing to a different resource.
- [x] Leave the active P5 settings JSON and service implementation untouched.
- [x] Run focused Work Management settings tests green.

### Task 5: Commissioning scripts and current documentation

**Modify:** GitHub/Supabase auth and smoke scripts, `README.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, `docs/OPERATIONS.md`, `docs/PROVIDER-MODULE-PRODUCT-SPEC.md`, and the current Supabase provider development README.
- [x] Update GitHub scripts/tests to validate the central project registry instead of requiring `settings/kis-repository.settings.json` as routing authority.
- [x] Update Supabase commissioning to select a registered KIS project, authenticate once against the unscoped endpoint, and call `get_project_url` with explicit `project_id`.
- [x] Update smoke modes so `SUPABASE_PROJECT_REF` is not required and shared-runtime verification expects the account-level surface plus registered project routing.
- [x] Update current authoritative/product documentation; preserve historical change records and explain legacy repository settings as compatibility only.
- [x] Run script/artifact tests and strict JSON/schema checks green.

### Task 6: Review, verification, PR, merge safety, and cleanup

- [x] Run focused tests for Projects, repositories/GitHub routing, Supabase, gateway, Work Management, and commissioning scripts.
- [x] Run the modularity collector again and compare dependency evidence; record `MAS = n/a` for any still-unmeasured dimensions rather than inventing scores.
- [x] Run `pwsh -NoProfile -File scripts/change-workflow.ps1 check` and `validate`.
- [x] Run canonical `pwsh -NoProfile -File scripts/verify.ps1` and capture exit status/material evidence.
- [x] Run independent code review against the complete branch diff; resolve all material findings and rerun affected checks.
- [x] Commit coherent implementation/documentation state, push the branch, and open PR #98 with requirement/test evidence.
- [x] Verify exact head `ba9ec4a0d6efe3fe99ee99c7eaac4175d1d24935` through Work Management #35 and merge only that verified head.
- [x] Update closeout evidence and confirm primary `main` contains merge `37adc01daf6703d164cd7b719872ffbfb55ed1c9`; governed cleanup follows after this metadata-only closeout lands.

## Recovery

Before merge, abandon/revert only this isolated branch if necessary. After merge, revert the PR if runtime commissioning exposes a material defect. Legacy repository settings remain readable during this migration, so rollback does not require touching target repositories.