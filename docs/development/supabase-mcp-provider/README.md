# Supabase MCP Provider

## Purpose

This module exposes the official hosted Supabase MCP server through standalone and shared `kis-mcp` runtimes. It is an approved external connector boundary, not a Desktop Commander Work invocation, and does not change HR-001, HR-002, or HR-003.

Use it only with a development or test Supabase project. The project-scoped upstream surface includes read/write tools, so do not commission it against production data.

## Configuration

The canonical settings file is `settings/providers/supabase-mcp.provider.json`.

The checked-in configuration:

- uses the official unscoped hosted streamable-HTTP endpoint `https://mcp.supabase.com/mcp`;
- uses OAuth 2.1 authorization-code flow with dynamic client registration once for the KIS runtime;
- persists OAuth client and token state through Windows Credential Manager under the configured `kis-mcp/supabase` keyring service;
- treats `SUPABASE_ACCESS_TOKEN` only as a legacy PAT conflict and never forwards it;
- defaults to the official read/write surface, with project routing enforced per call by the KIS project registry;
- leaves `features` empty so the official provider controls its default feature groups;
- stores project references only as non-secret routing coordinates in `settings/projects.settings.json`, never as OAuth credentials.

`SUPABASE_PROJECT_REF` is **not required** for provider startup or OAuth. Project-targeted upstream calls carry an explicit registered `project_id`; targetless calls are allowed only when the discovered upstream tool is explicitly read-only. Targetless mutating calls fail closed.

To request the upstream read-only surface, set `upstream.read_only` to `true`. To select official feature groups, add their upstream feature names to `upstream.features`. Neither setting creates a local tool-name allowlist.

When Windows credential storage is available and no legacy PAT conflict exists, `kis_provider_status` reports the provider ready for one account OAuth login. The authenticated connection and discovered tool surface are retained for the parent KIS runtime; explicit registered-project commissioning is tracked separately from account authentication.

## Preflight

Ensure the intended development or test project is registered in `settings/projects.settings.json` and clear the legacy PAT variable. No `SUPABASE_PROJECT_REF` environment variable is required:

```powershell
Remove-Item Env:SUPABASE_ACCESS_TOKEN -ErrorAction SilentlyContinue
```

Run the non-network preflight:

```powershell
pwsh -File .\scripts\smoke-supabase-mcp.ps1
```

The equivalent direct command is:

```powershell
C:\Projects\.kis-mcp\python-env\Scripts\python.exe -m kis_mcp.providers.supabase --check
```

Preflight validates strict provider settings, Windows keyring availability, and legacy PAT conflict state. It reports booleans and non-secret metadata only. It does not contact Supabase or prove authentication; project routing is validated separately against the central project registry.

## Browser OAuth commissioning

Run explicit commissioning from a supervised console:

```powershell
pwsh -File .\scripts\auth-supabase-mcp.ps1
```

FastMCP performs OAuth discovery, dynamic client registration, browser authorization, token refresh, and persistent storage through Windows Credential Manager against the unscoped account endpoint. The commissioning client then resolves the default registered KIS project and invokes only the harmless `get_project_url` read with its explicit registered `project_id`. It validates that the returned hostname matches that registry binding without printing the URL or project reference.

Read-only account discovery such as `list_projects` may remain available. Mutating tools may be discoverable but are never invoked by commissioning, and targetless mutations are rejected by routing.

## Shared runtime verification

After browser commissioning succeeds, verify token reuse and namespaced `supabase_*` exposure through the normal root server:

```powershell
pwsh -File .\scripts\smoke-supabase-mcp.ps1 -SharedRuntime
```

The shared smoke requires `kis_provider_status` to report Supabase as mounted, resolves the default project from the KIS project registry, and invokes only `supabase_get_project_url` with that explicit registered `project_id`. It returns boolean evidence and does not expose OAuth material, the project reference, or the project URL.

For a standalone live recheck, run:

```powershell
pwsh -File .\scripts\smoke-supabase-mcp.ps1 -Live
```

## Runtime and registration

The standalone endpoint remains available through:

```powershell
C:\Projects\.kis-mcp\python-env\Scripts\python.exe -m kis_mcp.providers.supabase
```

Normal startup is account-scoped and does not require `SUPABASE_PROJECT_REF`. When Windows credential storage is available without a legacy PAT conflict, FastMCP constructs one persistent OAuth-enabled upstream client against the unscoped endpoint, discovers the upstream tools once, and reuses that connection for the parent KIS runtime. Project authorization remains explicit per call through `settings/projects.settings.json`.

The shared Provider foundation is the integration boundary. This adapter exposes `build_provider_descriptor`, `provider_health`, and `register_provider(registry)` through `kis_mcp.providers.supabase`. Registration remains explicit and contains invalid Supabase configuration by leaving the provider absent; importing the adapter does not register, start, or contact the provider.

## Security and recovery

OAuth grants developer-level access to the selected organization and project. Review the browser authorization target and use only a development or test project.

Never place project references, PATs, OAuth access tokens, refresh tokens, client secrets, authorization codes, generated provider state, or logs in Git. `SUPABASE_ACCESS_TOKEN` must remain unset because PAT transport is no longer supported.

To recover from stale or invalid OAuth state:

1. stop standalone and shared provider processes;
2. revoke the Supabase authorization when appropriate;
3. remove the `kis-mcp/supabase` entries through Windows Credential Manager;
4. rerun `scripts\auth-supabase-mcp.ps1`;
5. repeat the shared-runtime smoke.

The commissioning and smoke workflows perform no Supabase mutation.
