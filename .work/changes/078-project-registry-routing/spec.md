# Change Specification: Project Registry Routing

- **Change ID**: `078-project-registry-routing`
- **Status**: Approved for implementation by the operator after design review
- **Risk Profile**: rigorous
- **Classification**: Complex

## Outcome

Make `kis-mcp` project-neutral across `C:\Projects` without putting KIS configuration in target repositories. Introduce one KIS-owned project registry for stable project identity and provider resource bindings, preserve global provider authentication, and route each operation using explicit project/repository identifiers.

## Authority and scope

- `AGENTS.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, `docs/OPERATIONS.md`, and current code/tests are authoritative.
- `docs/TRUST-MODEL.md` preserves the exact HR-001/HR-002/HR-003 runtime policy boundary.
- The operator-approved architecture in this conversation is the design authority for this change.
- Supabase behavior was independently verified against official Supabase MCP documentation and the mounted KIS provider before implementation.
- `scope.json` is the executable path boundary; active parallel claims remain untouched.

## Architectural decision

Project identity belongs in a focused `kis_mcp.projects` shared-kernel module, not in Providers, Work Management, Discover, or each target repository. Provider authentication remains provider-owned and process/runtime scoped. Project bindings are non-secret routing coordinates only.

There is no global mutable `active_project` authorization boundary. Operations remain explicit: local tools take paths, Work Management takes `project_id`, GitHub takes repository/Project coordinates, and Supabase takes upstream `project_id`. The registry validates those coordinates.
## Requirements

- **REQ-001 — Central registry:** Add strict versioned JSON settings containing stable `project_id`, display name, absolute local root, optional GitHub binding, and optional Supabase binding. Target repositories require no KIS file.
- **REQ-002 — Seeded projects:** Register `kis-mcp` and `gpt-os`. `kis-mcp` binds `NielPieterse0/kis-mcp`, user GitHub Project #1, and Supabase project ref `mmxuicfrdalymczdapjq`. No credential or publishable key is stored.
- **REQ-003 — Boundary validation:** Reject duplicate IDs/roots/provider resource identities, malformed GitHub coordinates, malformed project refs, and local roots outside `C:\Projects`.
- **REQ-004 — Repository compatibility:** Keep the legacy repository-settings API working for existing callers/tests, but allow a registry-backed selector to produce repository routing state without reading KIS settings from the target repo.
- **REQ-005 — GitHub authorization:** Keep the existing runtime-scoped OAuth/client lifecycle. Authorize GitHub repository and Project calls against all registered GitHub bindings rather than a process-global current target.
- **REQ-006 — Project UX:** Expose bounded read-only `kis_list_projects` and `kis_project_status(project_id)` operations through the gateway and retain the registry on `GatewayComposition`.
- **REQ-007 — Supabase global OAuth:** Connect OAuth to the unscoped official endpoint `https://mcp.supabase.com/mcp`. Remove the `SUPABASE_PROJECT_REF` provider-startup requirement.
- **REQ-008 — Supabase runtime lifetime:** Reuse the provider-neutral persistent FastMCP client lifecycle so one OAuth/account connection serves the parent KIS runtime.
- **REQ-009 — Supabase routing:** For upstream calls with `project_id`, require that value to match a registered Supabase project ref. Permit read-only account discovery without a project ID; reject targetless mutating account operations.
- **REQ-010 — Work-management bridge:** Keep feature/gate/evidence configuration in the existing work-management settings while resolving configured managed-project identity and GitHub Project coordinates from the registry when available.
- **REQ-011 — Commissioning:** Update GitHub and Supabase auth/smoke paths to use the project registry. Supabase commissioning proves account OAuth plus an explicit registered project read.
- **REQ-012 — Documentation:** Update current product, provider, platform, operations, and README documentation. Historical change records remain unchanged.
- **REQ-013 — Policy:** Do not add, remove, reinterpret, or weaken HR-001, HR-002, or HR-003.

## Modularity constraints

Measured 90-day seam evidence: Providers 6096 LOC / fan-in 12 / fan-out 11; Work Management 5212 / 8 / 5; Repositories 322 / 2 / 1; Gateway 389 / 2 / 3. RFC kinds, hidden coupling, and read-set/edit-set remain unavailable, so formal MAS is `n/a` rather than guessed.
The measured Provider seam is already highly connected. This change must not move project identity into Providers or create a universal provider-resource abstraction. `projects` is a small declared-contract module consumed by composition and adapters; it does not depend on Gateway, Providers, Work Management, or Discover.

## Acceptance

1. **Given** `C:\Projects\GPT-OS` has no KIS settings file, **when** KIS resolves `gpt-os`, **then** it returns its registered local/GitHub identity without requiring a file in GPT-OS.
2. **Given** a registered GitHub repository or Project coordinate, **when** a GitHub operation is authorized, **then** it is accepted independent of any mutable active-project state; an unregistered coordinate is rejected.
3. **Given** no `SUPABASE_PROJECT_REF` environment variable, **when** the Supabase provider starts, **then** it builds the unscoped OAuth transport and is locally ready when credential storage is available and no legacy PAT conflict exists.
4. **Given** Supabase project ref `mmxuicfrdalymczdapjq`, **when** a project-targeted upstream call supplies it as `project_id`, **then** routing accepts it; an unregistered project ID is rejected before upstream execution.
5. **Given** a targetless Supabase account mutation, **when** routing evaluates it, **then** it is rejected; bounded account discovery remains available.
6. **Given** current work-management settings, **when** they load, **then** their behavioral modes remain unchanged while KIS project identity/provider coordinates are registry-backed.
7. **Given** the gateway starts, **when** project catalogue operations are listed/called, **then** registered project metadata is available through bounded read-only operations.
8. **Given** existing legacy repository-settings tests/callers, **when** they use the legacy loader without a registry, **then** behavior remains compatible.
9. **Given** the final branch, **when** focused tests, governance checks, canonical verification, code review, and merge-head verification run, **then** all required checks pass before cleanup.

## Risks and recovery

- **Routing regression:** wrong provider target could be authorized. Mitigation: strict duplicate detection, allowlist tests, negative routing tests, explicit per-call identifiers.
- **OAuth regression:** changing Supabase endpoint/lifecycle could break commissioning. Mitigation: transport/lifecycle unit tests plus supervised live commissioning when available.
- **Parallel-work conflict:** active P5 and GitHub-experience changes own adjacent files. Mitigation: explicit exclusions and compatibility bridge; no edits to their owned paths.
- **Rollback:** revert the change PR. Legacy `settings/kis-repository.settings.json` remains supported as a compatibility path; no target repository is mutated.

## Out of scope

- Multi-user identity/auth profiles.
- Automatic enumeration or enrollment of `C:\Projects`.
- Adding KIS files to target repositories.
- Changing the exact three hard runtime policy rules.
- Rewriting the active P5 work-management service or the active GitHub provider-composition slice.
- Treating Supabase project refs or GitHub coordinates as credentials.