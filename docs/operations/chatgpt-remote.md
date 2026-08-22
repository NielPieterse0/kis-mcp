# ChatGPT Remote Runtime

> Operator runbook subordinate to [Operations](../OPERATIONS.md). Repository workflow and documentation routing remain in [AGENTS.md](../../AGENTS.md).

## Verify local ChatGPT HTTP transport

Run the local no-external-network smoke test before configuring a tunnel:

```powershell
pwsh -File .\scripts\smoke-chatgpt.ps1 -AllInstances -TimeoutSeconds 90
```

For each instance, the script starts the settings-defined loopback streamable HTTP endpoint, initializes MCP, lists tools, calls `kis_health`, calls bounded `inspect_project` against the repository root, verifies representative read/write/edit/process tools, writes and reads a unique marker beneath `C:\Projects\.kis-mcp\temp`, and quarantines the marker recoverably. `give_feedback_to_desktop_commander` remains absent because every invocation is external-network-only; ordinary mixed-purpose tools, `inspect_project`, and `inspect_change` remain exposed.

Use one instance when diagnosing a specific port or profile:

```powershell
pwsh -File .\scripts\smoke-chatgpt.ps1 -Instance development -TimeoutSeconds 90
```

This proves the local ChatGPT-compatible HTTP path. It does not prove the external tunnel or ChatGPT app connection.

## Configure a tunnel profile

For the selected instance:

1. Verify that its checked-in non-secret `tunnel_id`, vault secret reference, loopback URL, and `configured: true` state are correct.
2. Store the tunnel credential through the supervised application-vault script for that instance.
3. Create the project-local tunnel profile.
4. Run local and external commissioning checks before treating the instance as live.

```powershell
pwsh -File .\scripts\set-tunnel-credential.ps1 -Instance development
pwsh -File .\scripts\setup-tunnel.ps1 -Instance development
```

The credential script prompts through `Read-Host -AsSecureString` and stores the value at the selected instance's settings-defined non-secret `tunnel_secret_ref`. The setup script resolves that reference only through the secret-process boundary, exposes the value only through a temporary process-scoped environment reference for `tunnel-client init`, restores the prior process environment in `finally`, and writes generated profiles only to the settings-defined profile root.

The setup script reads the tunnel client path, profile name, tunnel ID, local MCP URL, and vault secret reference from JSON. It refuses to replace an existing profile unless `-BackupExistingProfile` is supplied; replacement first moves the old YAML profile into a timestamped backup. The vault secret is not copied into profile backups or repository files.

Configure the operation profile separately:

```powershell
pwsh -File .\scripts\set-tunnel-credential.ps1 -Instance operation
pwsh -File .\scripts\setup-tunnel.ps1 -Instance operation
```

The two profiles, tunnel IDs, and vault secret references must remain distinct. Do not point both instances at one tunnel record or one vault entry.

## Start the ChatGPT-facing instances

Use the same launcher for both ChatGPT tools. The preferred positional selectors are the external app names:

```powershell
pwsh -File .\scripts\start-chatgpt.ps1 kis-op
pwsh -File .\scripts\start-chatgpt.ps1 kis-dev
```

`kis-op` and `kis-dev` may run concurrently. The compatibility selectors `operation`, `op`, `development`, and `dev` resolve to the same canonical records. Omit the selector to use `settings.remote_mcp.active_instance`.

The launcher retrieves only the selected instance's tunnel secret from the application-managed vault, passes it through the owned process boundary, and clears temporary values after process creation. It then:

- validates the exact external app, internal instance, and canonical port mapping;
- runs lifecycle preflight only for the selected instance; the peer instance is neither inspected for cleanup nor stopped;
- accepts a clean selected-instance preflight with zero matching stale server or tunnel processes and reclaims matching stale processes only when they exist;
- reclaims a selected-instance listener or orphan process tree only when the canonical project Python launch path, exact remote-runtime instance, profile, and endpoint identity match; Windows may report the underlying base Python as `ExecutablePath`, so the canonical launch path may instead be proven by the first command-line token; an unrelated listener fails with PID/process diagnostics and is never terminated;
- enforces the external canonical Python environment and moves repository-local `.venv` or `.pytest_cache` transients into recoverable quarantine before startup;
- starts the selected remote runtime on that instance's settings-defined loopback endpoint;
- uses the launcher/settings-defined server/authentication budget and echoes retained server stderr live so OAuth/device-code guidance remains visible;
- proves MCP initialization and proves the new selected server process owns that exact listener before readiness;
- starts a fresh machine/tunnel readiness deadline only after the server/authentication phase has completed;
- writes one per-instance `current.json` ownership record while retaining timestamped startup/log evidence;
- starts only the selected tunnel profile and tunnel ID;
- waits for the selected tunnel client's loopback `/readyz` endpoint within the normal `TimeoutSeconds` budget;
- writes per-instance startup state and logs beneath the selected runtime directory;
- owns and cleans up only the server and tunnel processes created by that launcher invocation.

For `kis-mcp` itself, a landing on `main` performed through the KIS exact pull-request merge operation or the governed KIS merge-queue land operation emits one landed event to the shared runtime-composed post-land dispatcher, which receives the validated generated-state root from runtime configuration and schedules an automatic `kis-dev` refresh. Direct merge requires GitHub's reported merge commit as the exact landed synchronization reference; it does not substitute the PR head or a later branch-head read-back. If that exact landed identity is unavailable, restart is skipped and bounded failure evidence is retained without changing the authoritative merged result. On the first landing that introduces the worker script, the scheduler may launch that script from the currently executing source artifact while passing the primary repository root explicitly; the detached worker then waits briefly for the landing response to complete, requires that primary checkout to be clean and on `main`, fetches `origin/main`, accepts only a fast-forward local update, proves the required landed reference is contained by synchronized `main`, and invokes the synchronized primary `scripts/start-chatgpt.ps1 kis-dev`. Synchronization or restart failure is retained in bounded atomic development-runtime evidence. The latest receipt records both the triggering `landed_sha` and the actual synchronized `launched_sha`, so a later `main` advancement is explicit rather than misattributed, and failures still fail closed without resetting local Git state.

This post-land path is development-instance-only: it does not select, inspect for cleanup, stop, restart, or otherwise manage `kis-op`. Other registered repositories and non-`main` landing targets do not schedule it.

There is no automatic failover and no cross-instance process ownership. Keep each launcher window open while ChatGPT uses that tool.

## Create or switch the ChatGPT app

In ChatGPT developer-mode app settings, create a custom app using the Secure MCP Tunnel connection. Select the available tunnel or paste the instance's configured tunnel ID, then scan the tools. Confirm that the scanned catalogue includes representative filesystem, editing, terminal/process, and gateway operations. Do not accept a reduced profile-based catalogue.

The tunnel must be associated with the same ChatGPT workspace or organization that will use the app. Keep separate ChatGPT apps named `kis-op` and `kis-dev`, each associated with its own configured tunnel identity. Both may remain connected concurrently; never point both apps at the same tunnel identity.

A complete external commissioning record requires:

1. tunnel client readiness;
2. successful ChatGPT tool scan;
3. `kis_health` called from ChatGPT;
4. a supervised write/read/quarantine smoke operation beneath `C:\Projects`;
5. confirmation that the network-only feedback tool is absent while mixed-purpose tools remain available.
