# Operator Support

## Load when

Read this reference only for local startup, ChatGPT tunnel setup, provider
authentication, smoke testing, Control Center, repository verification,
governed worktrees, or startup troubleshooting.

Run operator scripts from the canonical kis-mcp repository checkout unless the
current script/document explicitly supports another root.

## Core local startup

Start the local stdio gateway:

```powershell
pwsh -NoProfile -File .\scripts\start.ps1
```

Start a ChatGPT-facing instance with the canonical external selector:

```powershell
pwsh -NoProfile -File .\scripts\start-chatgpt.ps1 kis-op
pwsh -NoProfile -File .\scripts\start-chatgpt.ps1 kis-dev
```

The compatibility selectors `operation`, `op`, `development`, and `dev` resolve
to the same configured instances. The supervised launcher owns only the selected
instance's server/tunnel processes and leaves the peer instance alone.

Normal configured startup resolves required application-vault secrets through
the verified current-user runtime unlock and injects them only into the selected
child process. Provider OAuth may still require its documented supervised
browser sign-in. Follow the checked-in launcher/status output when an older
running revision behaves differently.

## Tunnel credential and profile

Store/replace the selected instance credential only when changing it:

```powershell
pwsh -NoProfile -File .\scripts\set-tunnel-credential.ps1 -Instance development
```

Generate the profile:

```powershell
pwsh -NoProfile -File .\scripts\setup-tunnel.ps1 -Instance development
```

Use `-BackupExistingProfile` when intentionally replacing an existing profile.
Use `-ValidateLiveEndpoint` only when the selected local MCP endpoint is already
running and live validation is intended.

Normal startup should not require copying a tunnel secret or vault unlock into a
prompt, command argument, repository JSON, or profile YAML. A missing tunnel
credential remains a bounded startup/configuration problem; use the supervised
credential/configuration scripts and retry the selected instance.

## Local ChatGPT transport smoke

Run both instances without external tunnel dependence:

```powershell
pwsh -NoProfile -File .\scripts\smoke-chatgpt.ps1 -AllInstances -TimeoutSeconds 90
```

Or one instance:

```powershell
pwsh -NoProfile -File .\scripts\smoke-chatgpt.ps1 -Instance development -TimeoutSeconds 90
```

The smoke validates MCP initialization, representative direct tools, health,
bounded project inspection, a local write/read cycle, and recoverable
quarantine. It is local transport evidence, not proof of external tunnel or
ChatGPT commissioning.

## Provider onboarding

GitHub OAuth is runtime-owned. Use the repository helper when authentication is
required:

```powershell
pwsh -NoProfile -File .\scripts\auth-github-mcp.ps1
```

Keep the started operation runtime alive to reuse the authenticated provider
process. Restarting that runtime may require a new OAuth sign-in.

Use the GitHub smoke helper for non-live/runtime checks, and only request live
commissioning when operator-supervised authentication is intended:

```powershell
pwsh -NoProfile -File .\scripts\smoke-github-mcp.ps1
```

Supabase onboarding uses account-scoped OAuth plus explicit registered-project
routing. Use the checked-in `auth-supabase-mcp.ps1` and
`smoke-supabase-mcp.ps1` helpers for preflight, authentication, and bounded live
commissioning; do not reintroduce legacy PAT or implicit active-project routing.

Never place PATs, OAuth tokens, refresh tokens, API keys, tunnel credentials, or
provider-returned secrets in repository files or tool prompts.

## Control Center

Run the standalone read-only Control Center through the locked interpreter:

```powershell
C:\Projects\.kis-mcp\python-env\Scripts\python.exe -m kis_mcp.control_center
```

Use it for bounded runtime/project/policy/provider/quarantine/verification
status. It does not authorize changes.

## Repository verification

For kis-mcp itself, the canonical verification gate is:

```powershell
pwsh -NoProfile -File .\scripts\verify.ps1
```

It uses the locked external Python environment, performs offline/frozen
dependency synchronization, and runs configuration, syntax, governance, policy,
architecture, and full pytest verification.

Do not substitute a partial smoke test for this repository gate when preparing a
kis-mcp implementation change for completion.

## Governed change worktrees

List active claims:

```powershell
pwsh -NoProfile -File .\scripts\change-workflow.ps1 list
```

Create a change only after declaring a non-overlapping outcome and owned paths:

```powershell
pwsh -NoProfile -File .\scripts\change-workflow.ps1 new <change-id> --outcome <text> --owned <path>
```

From the change worktree, validate scope before review:

```powershell
pwsh -NoProfile -File .\scripts\change-workflow.ps1 check
```

After the branch is merged, cleanup must run from the clean primary checkout:

```powershell
pwsh -NoProfile -File .\scripts\change-workflow.ps1 cleanup <change-id>
```

Cleanup refuses dirty or unmerged worktrees and does not force branch deletion.

For change verification/review, prefer the current bounded change workflow when
it is advertised rather than manually assembling arbitrary process commands.
For PR preparation, active Slice 7 change `106-reviewable-pr-coordinator` targets
`prepare_reviewable_pull_request`: exact commit verification, exact registered
publication, exact PR creation/verification, then stop. Use it only after live
capability discovery confirms it is deployed. PR merge, branch deletion, and
worktree cleanup remain the separate safe-closeout path.

## Troubleshooting order

1. Read the bounded error code; distinguish structural/configuration errors from
   HR policy decisions.
2. Check `kis_health` for core local readiness.
3. Check `kis_provider_status` for provider-specific next action.
4. Use Control Center for a compact local status view when available.
5. Inspect the startup-state/log paths emitted by the launcher rather than
   relying on console noise.
6. Run the focused smoke that corresponds to the failing boundary.
7. Run canonical verification before claiming a repository implementation is
   complete.

Do not weaken policy, bypass project routing, or persist credentials merely to
make a smoke test pass.
