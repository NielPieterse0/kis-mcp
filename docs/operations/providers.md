# Provider Operations

> Operator runbook subordinate to [Operations](../OPERATIONS.md). Exact provider revisions, enabled tools, bindings, lifecycle contracts, and current commissioning state belong to provider settings/contracts/source/tests, [SPEC.md](../../SPEC.md), and live KIS status/evidence.

## Inspect provider runtime status

Call `kis_provider_status` before provider-specific work. Read registration/enablement, build/mount state, readiness, user status, and commissioning evidence separately; do not infer authentication or live verification from configuration alone.

Use the returned current next action. Resolve exact provider identity, modes, enabled tools, and registered bindings from the applicable `settings/providers/*.provider.json`, project registry, contracts, and runtime surface rather than copied prose.

### Activate and commission DBHub / Docker Hub

KIS startup/commissioning does not acquire provider source. Provision and build/stage the exact revision declared by the applicable provider settings in a separately supervised bootstrap step beneath `C:\Projects`.

Activate the verified local source roots:

```powershell
pwsh -NoProfile -File .\scripts\activate-db-docker-providers.ps1 `
  -DBHubSourceRoot C:\Projects\<exact-dbhub-checkout>\<deployment-subdir> `
  -DockerHubSourceRoot C:\Projects\<exact-dockerhub-checkout>\<deployment-subdir>
```

Then run bounded commissioning:

```powershell
pwsh -NoProfile -File .\scripts\commission-db-docker-providers.ps1
```

If activation or commissioning rejects revision, entry point, configuration, binding, credentials, or live verification, correct the named canonical input. Do not substitute `latest`, widen the provider surface, or weaken validation in the runbook.

For bounded Context7/Serena live smoke from the locked source environment:

```powershell
$env:UV_PROJECT_ENVIRONMENT='C:\Projects\.kis-mcp\python-env'
$env:UV_CACHE_DIR='C:\Projects\.kis-mcp\uv-cache'
uv run --offline --no-sync python scripts\run-provider-live-smoke.py
```

Use current provider settings/contracts for exact tested operations and state locations.

## Authenticate GitHub MCP

Ensure a legacy PAT override is not forcing a different authentication path:

```powershell
Remove-Item Env:GITHUB_PERSONAL_ACCESS_TOKEN -ErrorAction SilentlyContinue
pwsh -NoProfile -File .\scripts\auth-github-mcp.ps1
```

Complete the supervised browser/device authentication requested by the running provider and keep the selected runtime active. Then run the non-live focused smoke:

```powershell
pwsh -NoProfile -File .\scripts\smoke-github-mcp.ps1
```

Use `-RequireLive` only for an explicit supervised live recheck. Treat authentication/readiness as current-process evidence; use `kis_provider_status` rather than this document for current state.

## Commission Supabase OAuth

Use only an intended registered development/test project. Clear legacy PAT transport before preflight:

```powershell
Remove-Item Env:SUPABASE_ACCESS_TOKEN -ErrorAction SilentlyContinue
pwsh -File .\scripts\smoke-supabase-mcp.ps1
```

Start supervised browser OAuth:

```powershell
pwsh -File .\scripts\auth-supabase-mcp.ps1
```

After authorization, verify shared-runtime exposure:

```powershell
pwsh -File .\scripts\smoke-supabase-mcp.ps1 -SharedRuntime
```

Use an explicit standalone authenticated recheck only when required:

```powershell
pwsh -File .\scripts\smoke-supabase-mcp.ps1 -Live
```

Never place access/refresh tokens, client secrets, authorization codes, returned project URLs, or credential-store contents in repository files or logs.

For recovery, stop the relevant provider processes, revoke/remove the saved Supabase authorization through the supervised credential boundary when appropriate, rerun browser commissioning, and repeat the shared-runtime smoke. Exact endpoint, routing, and tool contracts remain owned by settings/source/contracts.