# Change Specification: Commissioning Refresh

- **Change ID**: `026-commissioning-refresh`
- **Status**: Approved for implementation
- **Development level**: Medium
- **Risk profile**: Standard

## Outcome

Present the commissioned GitHub and Supabase providers as ready for their next connection step instead of implying that an unconnected provider is broken.

## Authority and scope

- **Authoritative sources**: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, `policy/kis-mcp.policy.json`, `docs/OPERATIONS.md`.
- **Acceptance evidence**: the live end-to-end commissioning report supplied by the operator, focused provider tests, change-scope validation, and canonical repository verification.
- **Owned paths**: provider implementation and tests, the shared provider-status tool description, existing provider commissioning documentation, this change record, and the minimum authoritative status wording in `SPEC.md` and `docs/OPERATIONS.md`.
- **Excluded paths**: Discover implementation/tests, policy, tunnel commissioning, provider credentials, and unrelated runtime modules.
- **Dependencies**: current local `main` at `a73a19c6efbaf15b651cb05243f894e2a7623590`.

## Requirements

- **R1 — Supabase onboarding state**: When Supabase is commissioned locally but no project reference is present, the provider must remain mountable and observable and report `Ready — project initialization required`. Missing `project_ref` is an onboarding requirement, not a degraded provider.
- **R2 — Supabase authentication state**: When a project reference is present and local OAuth prerequisites are available, Supabase must report `Ready — authentication required` until live authentication is proven.
- **R3 — GitHub authentication state**: When the pinned GitHub executable and OAuth configuration are present, GitHub must report `Ready — authentication required` rather than failure-oriented or ambiguous `not_verified` wording.
- **R4 — Actionable shared status**: `kis_provider_status` must expose a provider-owned `user_status` and actionable commissioning states while preserving separate registration, build, mount, readiness, and live-verification evidence.
- **R5 — Genuine fault distinction**: Missing executables, unavailable credential storage, conflicting PAT configuration, invalid configuration, build failures, mount failures, and runtime failures must remain degraded, unavailable, or failed as appropriate.
- **R6 — Safe and bounded output**: Status output must remain deterministic, bounded, schema-compatible, and free of credentials, project references, OAuth material, or returned project URLs.
- **R7 — Guidance alignment**: Existing operations and provider guidance must explain the exact next action for GitHub and Supabase without claiming live authentication or upstream verification.
- **R8 — Boundary preservation**: The change must not alter HR-001, HR-002, HR-003, Discover behavior, provider authentication implementation, secrets handling, or external network policy.

## Acceptance

1. **Given** Supabase local configuration with Windows credential storage available and no project reference, **when** its descriptor and shared runtime are built, **then** it mounts a health-only local surface and reports `Ready — project initialization required` without attempting upstream transport creation.
2. **Given** Supabase local configuration with a project reference and no PAT conflict, **when** readiness is reported, **then** it reports `Ready — authentication required` and retains redacted OAuth details.
3. **Given** the pinned GitHub executable exists, **when** readiness is reported, **then** it reports `Ready — authentication required` and does not claim authentication or live verification.
4. **Given** provider-specific commissioning metadata, **when** `kis_provider_status` is called, **then** it preserves that metadata instead of replacing it with six generic `not_verified` values.
5. **Given** a genuine local provider fault, **when** readiness is aggregated, **then** the platform remains degraded or unavailable and the corrective action identifies the actual fault.
6. Focused provider tests, change-workflow check, whitespace validation, and `scripts/verify.ps1` pass on the final branch state.

## Risks and recovery

- **Risk**: Treating onboarding as ready could conceal a genuine prerequisite failure.
  **Control**: readiness distinguishes project/authentication actions from executable, credential-storage, PAT-conflict, build, and mount faults; tests cover each branch.
- **Risk**: A health-only Supabase mount could be mistaken for a live upstream tool surface.
  **Control**: mount, user status, authentication, upstream connection, tool discovery, and live verification remain separate fields.
- **Risk**: Status metadata could expose a project reference or secret.
  **Control**: only fixed state labels and instructions are added; existing redaction assertions remain and are expanded.
- **Recovery**: Revert the branch or restore the previous provider readiness/status implementation. No persistent data, credentials, schema migration, or external state is changed.

## Out of scope

- Repairing Discover Git metadata handling, Windows `list_processes`, usage telemetry, recent-call coverage, or stopped-search reporting.
- Performing GitHub or Supabase authentication.
- Storing a Supabase project reference in repository JSON.
- Changing provider versions, OAuth mechanics, credential storage, repository scope, or tool namespaces.
