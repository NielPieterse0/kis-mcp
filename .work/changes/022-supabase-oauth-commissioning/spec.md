# Change Specification: Supabase OAuth Commissioning

- **Change ID:** `022-supabase-oauth-commissioning`
- **Status:** Approved by operator request to continue Slice C
- **Development level:** Complex — external OAuth, persistent credentials, remote provider lifecycle, and live project-scoped verification

## Outcome

Commission the official hosted Supabase MCP endpoint through OAuth 2.1 dynamic client registration, persist OAuth client and token state in Windows Credential Manager, preserve mandatory project scoping, prove one harmless project-scoped read, and prove the provider through the shared `kis-mcp` runtime under the existing `supabase_*` namespace.

## Approved boundary

Merged provider-runtime evidence defines Slice C as:

1. hosted OAuth/DCR;
2. approved persistent token storage;
3. a harmless project-scoped read;
4. main-endpoint live verification.

The official hosted endpoint remains `https://mcp.supabase.com/mcp`. `project_ref` remains mandatory and disables account-level tools. The official server performs OAuth discovery and DCR. FastMCP 3.4.4 provides OAuth authorization-code flow, DCR, refresh, and pluggable `AsyncKeyValue` token storage.

## Selected design

- Replace PAT bearer authentication with FastMCP `OAuth`.
- Persist OAuth tokens and dynamically registered client information through `key_value.aio.stores.keyring.KeyringStore`, which uses Windows Credential Manager on Windows.
- Keep `SUPABASE_PROJECT_REF` as the supervised runtime scope input.
- Retain `SUPABASE_ACCESS_TOKEN` only as a redacted legacy-conflict signal; never forward it.
- Use a stateful proxy client so one upstream MCP session serves the provider process.
- Commission explicitly through `scripts/auth-supabase-mcp.ps1` before shared-runtime use.
- Verify `get_project_url` succeeds with no arguments in project-scoped mode.
- Verify `list_projects` is absent and mutating project-scoped tools remain discoverable without invoking them.
- Verify `kis_provider_status`, `supabase_get_project_url`, and namespaced scope behavior through normal `build_server()`.

## Requirements

- **REQ-001:** Strict schema version 2 permits only OAuth/DCR and Windows-keyring token persistence.
- **REQ-002:** No PAT, OAuth token, refresh token, client secret, authorization code, or project reference value is serialized or logged.
- **REQ-003:** Provider startup requires a non-empty project reference but does not require pre-existing OAuth tokens.
- **REQ-004:** The upstream URL always includes encoded `project_ref`; configured `read_only` and `features` map only to official query parameters.
- **REQ-005:** The transport uses FastMCP OAuth with the exact upstream URL and project-specific Windows Credential Manager service.
- **REQ-006:** Local readiness separates project scope and credential-store availability from authenticated/live state.
- **REQ-007:** Browser commissioning proves required tool surface, OAuth identity, harmless `get_project_url`, and absence of account-level `list_projects`.
- **REQ-008:** Shared-runtime smoke proves the provider is mounted and exercises `supabase_get_project_url` through the root server.
- **REQ-009:** Commissioning performs no Supabase mutation.
- **REQ-010:** Existing GitHub, Work, Discover, Skills, policy, quarantine, shared runtime, and tunnel implementation remain unchanged.
- **REQ-011:** `SPEC.md` and `docs/OPERATIONS.md` report current GitHub and Supabase commissioning truthfully.
- **REQ-012:** Focused tests, live commissioning, shared-runtime smoke, scope validation, JSON validation, whitespace validation, and full verification pass.

## Acceptance

1. Checked-in settings contain OAuth/DCR metadata and no credential values.
2. `build_server()` constructs without a PAT and without performing network access.
3. The first explicit commissioning run opens Supabase authorization and persists state in Windows Credential Manager.
4. A later shared-runtime run reuses persistent OAuth state without requiring a PAT.
5. `get_project_url` succeeds for the configured project; `list_projects` is absent.
6. The shared catalogue contains the expected `supabase_*` surface and reports mounted status.
7. No write tool is invoked during verification.
8. Current repository verification passes with no changes outside the declared scope.

## Risks and recovery

- OAuth grants developer-level project access. Use only a development or test project and review the organization selected during authorization.
- Windows Credential Manager entries survive process restart. Revoke the Supabase authorization and remove the `kis-mcp/supabase` credentials through Windows Credential Manager when decommissioning or recovering from stale state.
- Windows Credential Manager values are bounded; an oversized token/client record must fail visibly rather than fall back to plaintext files.
- If shared-runtime OAuth reuse fails, stop the provider, revoke/remove stored entries, rerun explicit commissioning, and repeat live smoke.

## Out of scope

- Production Supabase data.
- Creating or changing Supabase projects.
- Database, schema, Edge Function, branch, storage, or account mutations.
- Custom Supabase tool allowlists.
- File-based plaintext token storage.
- Changes to shared provider composition or Work authorization.
