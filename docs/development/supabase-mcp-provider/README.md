# Supabase MCP Provider

## Purpose

This module exposes the official hosted Supabase MCP server through standalone and shared `kis-mcp` runtimes. It is an approved external connector boundary, not a Desktop Commander Work invocation, and does not change HR-001, HR-002, or HR-003.

Use it only with a development or test Supabase project. The project-scoped upstream surface includes read/write tools, so do not commission it against production data.

## Configuration

The canonical settings file is `settings/providers/supabase-mcp.provider.json`.

The checked-in configuration:

- uses the official hosted streamable-HTTP endpoint;
- requires one project reference through `SUPABASE_PROJECT_REF`;
- uses OAuth 2.1 authorization-code flow with dynamic client registration;
- persists OAuth client and token state through Windows Credential Manager under the configured `kis-mcp/supabase` keyring service;
- treats `SUPABASE_ACCESS_TOKEN` only as a legacy PAT conflict and never forwards it;
- defaults to project-scoped read/write operation;
- leaves `features` empty so the official provider controls its default feature groups;
- stores configuration and environment-variable names only, never project references or credential values.

To request the upstream read-only surface, set `upstream.read_only` to `true`. To select official feature groups, add their upstream feature names to `upstream.features`. Neither setting creates a local tool-name allowlist.

Before a repository is linked, `kis_provider_status` reports **`Ready — project initialization required`** and mounts the local `supabase_kis_supabase_health` surface without constructing an upstream transport. This means the provider is commissioned and available for setup; it does not mean Supabase is broken or degraded. After `SUPABASE_PROJECT_REF` is set and local OAuth prerequisites pass, the state becomes **`Ready — authentication required`** until browser authorization and live verification are completed.

## Preflight

Set `SUPABASE_PROJECT_REF` in the supervised operator environment and clear the legacy PAT variable:

```powershell
$env:SUPABASE_PROJECT_REF = '<development-project-ref>'
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

Preflight validates strict settings, project-scope presence, Windows keyring availability, and legacy PAT conflict state. It reports booleans and non-secret metadata only. It does not contact Supabase or prove authentication.

## Browser OAuth commissioning

Run explicit commissioning from a supervised console:

```powershell
pwsh -File .\scripts\auth-supabase-mcp.ps1
```

FastMCP performs OAuth discovery, dynamic client registration, browser authorization, token refresh, and persistent storage through Windows Credential Manager. The commissioning client discovers the project-scoped tool surface and invokes only the harmless `get_project_url` read with `{}`. It validates that the returned hostname matches the configured project reference without printing the URL or project reference.

`list_projects` must remain absent in project-scoped mode. Mutating project-scoped tools may be discoverable but are not invoked by commissioning.

## Shared runtime verification

After browser commissioning succeeds, verify token reuse and namespaced `supabase_*` exposure through the normal root server:

```powershell
pwsh -File .\scripts\smoke-supabase-mcp.ps1 -SharedRuntime
```

The shared smoke requires `kis_provider_status` to report Supabase as mounted and invokes only `supabase_get_project_url` with `{}`. It returns boolean evidence and does not expose OAuth material, the project reference, or the project URL.

For a standalone live recheck, run:

```powershell
pwsh -File .\scripts\smoke-supabase-mcp.ps1 -Live
```

## Runtime and registration

The standalone endpoint remains available through:

```powershell
C:\Projects\.kis-mcp\python-env\Scripts\python.exe -m kis_mcp.providers.supabase
```

Normal startup does not require a project reference merely to mount and report provider health. Without `SUPABASE_PROJECT_REF`, the adapter exposes only its local health tool and reports project initialization as the required next step. Once project scope is present and Windows credential storage is available without a legacy PAT conflict, the project reference is encoded as the official `project_ref` query parameter, FastMCP constructs the OAuth-enabled upstream HTTP transport, and the provider reports authentication as the required next step.

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
