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

For bounded Context7/Serena live smoke from the locked source environment, invoke the already-built environment directly so verification does not depend on whichever `uv.exe` happens to resolve from the operator PATH:

```powershell
C:\Projects\.kis-mcp\python-env\Scripts\python.exe scripts\run-provider-live-smoke.py
```

Serena installation resolves the signed shared-system Python through `scripts/runtime-authority.ps1`, records that host identity in acquisition/candidate manifests, and builds the candidate venv from that exact interpreter. Node host trust is classified independently from provider-native `.node` helpers; a valid OpenJS signature on `node.exe` is not evidence that a loaded native helper is trusted. Use current provider settings/contracts for exact tested operations and state locations, and correlate the canonical workload with fresh Code Integrity 3033/3077 events when validating Defender/SAC conformance.

## Authenticate GitHub MCP

Ensure a legacy PAT override is not forcing a different authentication path:

```powershell
Remove-Item Env:GITHUB_PERSONAL_ACCESS_TOKEN -ErrorAction SilentlyContinue
pwsh -NoProfile -File .\scripts\auth-github-mcp.ps1
```

Start the selected runtime. KIS first checks the configured GitHub CLI authentication state and, when it is valid, passes that CLI-managed credential only to the fresh GitHub MCP child process. No browser/device prompt is expected on that path. If the shared CLI credential is unavailable or invalid, complete the supervised provider browser/device OAuth fallback. Then run the non-live focused smoke:

```powershell
pwsh -NoProfile -File .\scripts\smoke-github-mcp.ps1
```

Use `-RequireLive` only for an explicit supervised live recheck. Treat authentication/readiness as current-process evidence; use `kis_provider_status` rather than this document for current state.

## Supabase is parked

Supabase implementation, OAuth/configuration, routing, and standalone smoke scripts remain preserved for a future operator-approved activation. Normal KIS composition intentionally does not register, mount, catalogue, report, recommend, or expose Supabase, even though retained configuration may still contain a Supabase runtime record.

Do not run Supabase OAuth or shared-runtime commissioning as normal operations. A future activation must be authorized by the operator, update the applicable canonical runtime/configuration authority, and verify the then-current FastMCP/provider contract before any Supabase surface is exposed.

Until that activation, `kis_provider_status`, capability search, and the normal tool surface must contain no Supabase provider/status/setup prompt or `supabase_*` operation. Existing credentials, if any, do not make Supabase active.