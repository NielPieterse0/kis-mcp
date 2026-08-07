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

Start a ChatGPT-facing instance:

```powershell
pwsh -NoProfile -File .\scripts\start-chatgpt.ps1 -Instance operation
pwsh -NoProfile -File .\scripts\start-chatgpt.ps1 -Instance development
```

The supervised launcher owns only the selected instance's server/tunnel process
and should leave the peer instance alone.

Startup hardening is being changed concurrently. When the checked-in/live
`start-chatgpt.ps1` includes the 077 hardening, normal startup should not prompt
for a generic vault unlock: server startup is direct and the tunnel credential
is retrieved non-interactively from the current Windows user's approved
credential entry. On an older instance, follow the current checked-in script and
report the older behavior rather than presenting the pending change as deployed.

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

Under the 077-hardened startup path, normal startup should not ask the operator
to unlock the generic application vault. A missing tunnel credential remains a
bounded startup/configuration problem; do not solve it by writing a secret into
repository JSON or profile YAML. If 077 is not present in the running revision,
describe that revision's behavior explicitly instead of silently assuming it.

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

Supabase onboarding is evolving toward project-neutral account OAuth plus
explicit project routing. Use the **current checked-in** `auth-supabase-mcp.ps1`
and `smoke-supabase-mcp.ps1` help/current operations guidance rather than
persisting an older environment-variable recipe in this skill.

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
