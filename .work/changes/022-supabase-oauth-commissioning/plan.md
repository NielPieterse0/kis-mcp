# Supabase OAuth Commissioning Plan

## Goal

Replace the legacy PAT-based Supabase adapter runtime with hosted OAuth/DCR, persist OAuth state in Windows Credential Manager, and prove project-scoped access through the shared runtime.

## Tasks

### 1. Reconcile governance and baseline

- Close the stale merged `009-supabase-mcp-provider` claim.
- Validate the new claim from the emergency worktree.
- Run baseline focused and full verification.

### 2. Configuration contract — TDD

- Add failing tests for schema version 2, OAuth-only mode, keyring service, callback settings, and legacy PAT conflict metadata.
- Update JSON, JSON Schema, immutable config model, and strict loader.
- Verify unknown keys and PAT-era configuration fail structurally.

### 3. OAuth storage and readiness — TDD

- Add failing tests for project-scoped URL construction without PAT requirements.
- Add a focused Windows Credential Manager storage factory using `KeyringStore` and sanitization strategies.
- Report storage availability and `authenticated=not_verified` without enumerating or returning secret values.
- Reject explicit commissioning when the legacy PAT environment variable is populated.

### 4. Stateful OAuth proxy — TDD

- Add failing transport/server tests for FastMCP `OAuth`, persistent keyring storage, and stateful proxy construction.
- Replace bearer auth and stateless proxy construction.
- Keep provider registration and shared runtime composition boundaries unchanged.

### 5. Explicit commissioning — TDD

- Add a commissioning module and PowerShell launcher.
- Require `get_project_url`, `list_tables`, and one representative mutating tool in the surface.
- Call only `get_project_url`.
- Prove `list_projects` is absent in project-scoped mode.
- Return booleans and tool names only; never return project URLs or credentials.

### 6. Shared-runtime smoke — TDD

- Extend the smoke path to build normal `kis-mcp`, verify mounted status, and call `supabase_get_project_url`.
- Prove `supabase_list_projects` is absent and a namespaced mutating tool is discoverable but not invoked.

### 7. Documentation and implementation status

- Update provider-specific operations and verification evidence.
- Reconcile stale GitHub/Supabase commissioning statements in `SPEC.md` and `docs/OPERATIONS.md`.

### 8. Review and verification

- Review the complete diff for secret handling, scope, lifecycle, OAuth failure paths, false-positive commissioning, and unnecessary complexity.
- Run focused tests, explicit OAuth commissioning, shared-runtime live smoke, scope check, JSON validation, whitespace validation, and full `scripts/verify.ps1`.
- Record exact evidence and residual limitations, then commit, push, and open the PR without merging.
