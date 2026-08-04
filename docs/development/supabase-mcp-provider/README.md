# Supabase MCP Provider

## Purpose

This module exposes the official hosted Supabase MCP server through a standalone kis-mcp stdio endpoint. It is an approved external connector boundary, not a Desktop Commander Work invocation, and does not change HR-001, HR-002, or HR-003.

Use it only with a development or test Supabase project. The upstream provider can read and mutate database and project resources, so do not connect it to production data.

## Configuration

The canonical settings file is `settings/providers/supabase-mcp.provider.json`.

The checked-in configuration:

- uses the official hosted streamable-HTTP endpoint;
- requires one project reference through `SUPABASE_PROJECT_REF`;
- requires a scoped personal access token through `SUPABASE_ACCESS_TOKEN`;
- defaults to project-scoped read/write operation;
- leaves `features` empty so the official provider controls its default feature groups;
- stores environment-variable names only, never credentials.

To request the upstream read-only surface, set `upstream.read_only` to `true`. To select official feature groups, add their upstream feature names to `upstream.features`. Neither setting creates a local tool-name allowlist.

## Runtime

Provide `SUPABASE_PROJECT_REF` and `SUPABASE_ACCESS_TOKEN` in the supervised operator environment. Use a development-project reference and a dedicated scoped token; do not write either value into repository files.

Run the non-network readiness check:

```powershell
pwsh -File .\scripts\smoke-supabase-mcp.ps1
```

The equivalent direct command is:

```powershell
C:\Projects\.kis-mcp\python-env\Scripts\python.exe -m kis_mcp.providers.supabase --check
```

The check validates settings and reports only booleans for project-reference and token presence. It never prints either value and does not contact Supabase.

Start the standalone stdio endpoint:

```powershell
C:\Projects\.kis-mcp\python-env\Scripts\python.exe -m kis_mcp.providers.supabase
```

Normal startup requires both environment variables. The bearer token is supplied only to FastMCP's upstream HTTP transport, while the project reference is encoded as the official `project_ref` query parameter.

## Security and recovery

Use a dedicated token with the narrowest available Supabase account access and rotate it outside the repository. Never place tokens, project references, generated OAuth state, or provider logs in Git.

To disable the connector, stop the standalone process and remove its client connector entry. The module performs no installation-time database migration and stores no credentials.

Central registry composition is intentionally deferred because the concurrent GitHub-provider slice owns `src/kis_mcp/provider_registry.py`. This module exposes an immutable descriptor for later registration after that slice lands.
