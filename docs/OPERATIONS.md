# Operations

## Prerequisites

- Windows with PowerShell.
- Python 3.11 or newer.
- `uv` for the Python environment.
- Node.js 18 or newer with npm.
- Direct operator supervision for bootstrap and upgrades.

## Deployment model

`kis-mcp` is operated from a supervised source checkout. The checkout root is the authoritative configuration root and must contain:

- `settings/kis-mcp.settings.json`
- `policy/kis-mcp.policy.json`

A standalone wheel installation is not a supported deployment model. Starting the runtime without those canonical JSON files fails with `KIS_MCP_SOURCE_CHECKOUT_REQUIRED` and identifies the resolved root and missing files. Run the CLI and scripts from the repository checkout; generated state remains beneath `C:\Projects\.kis-mcp` as described below.

## Generated state

All generated state remains inside the approved write boundary and outside the repository:

```text
C:\Projects\.kis-mcp\
├── .claude-server-commander\
├── desktop-commander\
├── tools\
│   ├── agentsys\6.0.1\
│   └── agnix\0.45.0\
├── agent-hosts\
│   └── agentsys\
├── python-env\
├── uv-cache\
├── python-cache\
├── pytest-cache\
├── npm-cache\
├── quarantine\
├── tunnel-client\
│   ├── profiles\
│   └── runtime\
│       ├── operation\
│       └── development\
├── temp\
└── logs\
```

Do not commit this state. Repository-local `.venv`, `.pytest_cache`, PowerShell module cache, provider state, or command-state directories are not authoritative project artifacts.

## Install Python dependencies

Run the operator-supervised bootstrap from `C:\Projects\kis-mcp`:

```powershell
pwsh -File .\scripts\bootstrap-python.ps1
```

The script may use external network access, generates or updates `uv.lock`, and synchronizes the locked development environment beneath `C:\Projects\.kis-mcp\python-env`. It also keeps uv, Python bytecode, pytest, and temporary state outside the repository.

Normal startup and verification never resolve or update dependencies from the network. `scripts\verify.ps1` requires `uv.lock` and performs an offline frozen synchronization before testing.

## Install Desktop Commander

Desktop Commander is installed from the scanned `@wonderwhy-er/desktop-commander` archive, not copied into this repository and not downloaded again by the installer.

Archive acquisition and security scanning are explicit operator-supervised actions outside the normal Work path. The repository installer itself performs no external network access:

```powershell
pwsh -File .\scripts\install-desktop-commander.ps1
```

The script reads the exact archive file name and SHA-256 from `settings/kis-mcp.settings.json`, resolves that archive beneath the current user's `Downloads` directory, verifies the digest before creating installation state, resolves `node.exe` and `npm.cmd`, and invokes npm with `--offline` and `--ignore-scripts`.

Installation is staged beneath `C:\Projects\.kis-mcp\temp` and activated beneath `C:\Projects\.kis-mcp\desktop-commander` only after package identity, version, and entry-point checks pass. Any prior installation is retained as a recoverable backup beneath the project temporary root.

The scanned Desktop Commander `.tgz` does not bundle its runtime dependency closure. Every dependency must therefore already exist in the project-local, separately scanned npm cache at `C:\Projects\.kis-mcp\npm-cache`. If any dependency is absent, the installer fails with `DESKTOP_COMMANDER_OFFLINE_INSTALL_FAILED`; do not remove `--offline` or allow a registry fallback.

Prepare the dependency cache in a separate operator-supervised network stage:

```powershell
pwsh -File .\scripts\prepare-desktop-commander-cache.ps1
```

This script verifies the same local archive and SHA-256, uses that archive as the root package source, downloads its dependency closure into a unique temporary acquisition area beneath `C:\Projects\.kis-mcp\temp`, disables package scripts, verifies the installed package identity and version, scans the complete acquisition tree with Microsoft Defender, and promotes only the clean npm cache. It retains any previous cache as a recoverable temporary backup. It does not download a second Desktop Commander root package.

After the preparation succeeds, rerun the unchanged offline installer:

```powershell
pwsh -File .\scripts\install-desktop-commander.ps1
```

Normal startup uses the installed package without downloading or updating it.

## Install managed AgentSys and agnix tooling

AgentSys and agnix are optional supervised host tools. They are installed independently, pinned to exact versions, and are not mounted into `build_server()`.

```powershell
pwsh -NoProfile -File .\scripts\install-agentsys.ps1
pwsh -NoProfile -File .\scripts\install-agnix.ps1
```

The installers may use external network access during this explicit bootstrap stage. They stage and validate package and profile state beneath `C:\Projects\.kis-mcp\temp`, reject paths outside `C:\Projects` or through reparse ancestors, and move replaced or failed-new state beneath quarantine rather than deleting it.

AgentSys `6.0.1` creates isolated managed profiles for Claude Code, OpenCode, and Codex. The corresponding host executable and authentication remain separate prerequisites. Start a host through the managed launcher:

```powershell
pwsh -NoProfile -File .\scripts\start-agentsys-host.ps1 -Platform claude
pwsh -NoProfile -File .\scripts\start-agentsys-host.ps1 -Platform opencode
pwsh -NoProfile -File .\scripts\start-agentsys-host.ps1 -Platform codex
```

agnix `0.45.0` provides the verified `agnix` CLI. Its npm distribution does not include the separate native `agnix-mcp` binary, so MCP mounting remains deferred and must not be inferred from the CLI installation.

See [`development/bootstrap/agentsys.md`](development/bootstrap/agentsys.md) and [`development/bootstrap/agnix.md`](development/bootstrap/agnix.md) for exact managed paths, catalogue counts, launch prerequisites, and recovery.

## Configure

Edit only the canonical JSON files:

- `settings/kis-mcp.settings.json` for identity, paths, Desktop Commander version and launch settings, Discover retrieval settings, local stdio transport, ChatGPT remote transport, and informational implementation status.
- `settings/providers/platform-runtime.provider.json` for the exact approved mounted MCP provider IDs, runtime enablement, and unique lower-case namespaces. Do not place credentials in this file.
- `settings/providers/github-mcp.provider.json` for GitHub provider identity, pinned source/executable, OAuth mode, PAT-conflict metadata, and toolsets only. Do not place repository or Project routing in provider authentication settings.
- `settings/kis-repository.settings.json` for repository identity, the matching `github_repository`, and repository-local `gh_projects` bindings. The loader validates the declared GitHub repository against local `origin` when available.
- `settings/agents/code-review-agent.settings.json` for the one advisory code-review agent, NVIDIA NIM and Codex CLI backend configuration, preferred/fallback order, and evidence/output budgets. Store only the `NVIDIA_API_KEY` environment-variable name, never the API key value.
- `settings/capabilities.settings.json` for suitability and intrinsic-quality weights, the bounded direct profile, discovery operations, readiness penalty, and reviewed capability metadata for every current shared Skill.
- `policy/kis-mcp.policy.json` for the exact three-rule declaration.

The policy file must contain exactly HR-001, HR-002, and HR-003. Adding, removing, or weakening a rule requires explicit operator approval.

The normal approved boundary is `C:\Projects`. State and quarantine roots must remain true descendants of it.

`settings.discover` owns all Discover retrieval behavior: enablement, exclusions, allowed text extensions and conventional filenames, encodings, hard-link handling, and file, directory, byte, depth, traversal-time, Git, Python-index, evidence, and output budgets. Change those values in JSON rather than hard-coding new limits or exclusions. Request-side limits may only narrow configured maxima.

`settings.remote_mcp` contains two canonical internal instances and external ChatGPT app identities:

- `operation` — exposed as `kis-op` on `127.0.0.1:8010` for normal operation;
- `development` — exposed as `kis-dev` on `127.0.0.1:8011` for commissioning and change validation.

Each instance has its own app name, loopback port, tunnel profile, explicit `configured` state, non-secret `tunnel_id`, vault secret reference, runtime directory, and logs. Startup validates the exact app/instance/port mapping and rejects swapped, changed, or duplicate ports. The secret is not stored in JSON or generated state. The tunnel executable is read only from:

```text
C:\Tools\openai-tunnel-client\tunnel-client.exe
```

The checked-in `operation` and `development` records contain distinct non-secret tunnel IDs and vault secret references and are marked `configured: true`. This configuration does not prove that the referenced vault entries, generated profiles, external tunnels, ChatGPT discovery, or end-to-end commissioning are ready. Before tunnel setup or startup, verify the selected record, store its secret through the supervised vault script, and generate the corresponding profile. Do not commit credential values or generated profile YAML.

`active_instance` controls the default only. Prefer the external selectors `kis-op` and `kis-dev`; the compatibility names `operation` and `development` and short aliases `op` and `dev` resolve to the same canonical records. There is no automatic failover.

Configuration, instance selection, catalogue metadata, profiles, readiness, scores, and status fields do not create another Work rule. Both instances compose the same backend capabilities and use the same bounded direct profile. Eligible long-tail operations remain discoverable and effect-dispatched through their original schemas and middleware; both instances still apply only HR-001, HR-002, and HR-003 to concrete Work invocations.

## Start local stdio

Run:

```powershell
pwsh -File .\scripts\start.ps1
```

Startup does not install or update packages. It requires the external locked Python environment and the pinned Desktop Commander entry point to exist, validates the exact three-rule set and canonical state paths, validates provider offline readiness, and then starts `kis-mcp` over stdio using `C:\Projects\.kis-mcp\python-env\Scripts\python.exe`.

Provider readiness rejects enabled telemetry, a missing or non-loopback feature-flag URL, and missing local Chrome when configured as required because the pinned provider source proves those states cause automatic external activity. It also requires Desktop Commander's persisted `blockedCommands` and `allowedDirectories` fields to remain empty so the provider cannot add independent command or directory restrictions beneath FastMCP.

After the core gateway is created, startup loads the strict provider-runtime JSON and attempts enabled GitHub, Supabase, and Control Center adapter builds in stable provider-ID order. Successful adapters mount as `github_*`, `supabase_*`, and `controlcenter_*`. NVIDIA NIM is registered in the Provider catalogue but is consumed only by the advisory agent rather than mounted as a general provider passthrough. Codex CLI is a local Tool-registry adapter behind the same agent. Missing binaries, credentials, invalid builder results, transport failures, or mount failures do not prevent the Work, Discover, Skills, agent-registration, or gateway surfaces from starting. Invalid provider-runtime JSON remains a startup configuration error. Missing or invalid agent JSON disables only the optional code-review agent and its NVIDIA/Codex backends.

For GitHub, the Provider runtime creates one shared FastMCP client and keeps its upstream GitHub MCP subprocess connected for the lifetime of the parent `kis-op` process. Before the mounted provider lifespan starts, aggregate tool inspection exposes only the GitHub adapter's local surface and deliberately does not connect the upstream GitHub process. After the shared client connects, a single `get_me` startup call triggers OAuth and initial upstream tool discovery publishes the current runtime tool snapshot without closing that connection. Downstream tool sessions reuse the authenticated process; stopping or restarting `kis-op` closes it and requires one new sign-in on the next start. Repository and Project authorization are evaluated separately from `settings/kis-repository.settings.json` on each GitHub call. Changing the selected repository context does not reconnect the authenticated GitHub client.

The feedback tool and `read_file.isUrl` mode are absent from the Work contract. Terminal and process tools remain available. The gateway builds the static/local capability surface without forcing GitHub upstream discovery, then augments the effective capability catalogue from current provider runtime-tool snapshots and current readiness whenever discovery, recommendation, eligibility, or long-tail dispatch is evaluated. The bounded direct `tools/list` profile remains fixed for the running gateway; newly discovered long-tail operations remain discoverable rather than automatically becoming direct tools. The gateway still blocks or transforms only concrete HR-001, HR-002, or HR-003 effects.

## Use capability discovery and long-tail execution

The normal MCP tool list is deliberately bounded by `settings/capabilities.settings.json`. Frequent file, process, health, provider-status, primary Discover, advisory-review, capability-discovery, effect-specific dispatch, and Control Center entry points remain direct. Other valid operations remain registered but do not consume equal default context.

Use:

- `search_capabilities(query, limit)` to locate operations across Providers, Tools, Discover, Skills, and Workflows and inspect readiness and eligibility;
- `describe_capability(capability_id)` to inspect normalized contribution, operation, and workflow metadata;
- `recommend_workflow(task)` to retrieve complete task-level workflow recommendations;
- `execute_read_action(operation, arguments)` for eligible read-only long-tail operations;
- `execute_change_action(operation, arguments)` for eligible local-change, quarantine, or process operations;
- `execute_external_action(operation, arguments)` for eligible external operations.

Dispatch always re-enters the original FastMCP tool with `run_middleware=True`. Original schemas remain authoritative. A generic parameters object does not weaken validation. The external dispatcher refuses operations that still require their own approval workflow. Unavailable, disabled, authentication-gated, build-failed, and mount-failed operations remain visible in status and catalogue results but are not dispatched.

Tool quality and suitability scores are recommendation evidence only. They never authorize a call, override HR-001, HR-002, or HR-003, or replace provider authentication and commissioning.

## Configure work management

Work management uses `settings/work-management/github-projects.settings.json` and remains disabled by default. Before enabling it:

1. confirm each managed repository and local root;
2. assign a valid GitHub Project owner, owner type, and Project number;
3. start `kis-op` and complete the one supervised GitHub OAuth sign-in required for that runtime;
4. run settings validation and a read-only inventory check;
5. review reconciliation previews before any apply operation.

Use the fixed-shape CLI:

```powershell
pwsh -NoProfile -File .\scripts\project-workflow.ps1 settings --settings settings\work-management\github-projects.settings.json
pwsh -NoProfile -File .\scripts\project-workflow.ps1 status --settings settings\work-management\github-projects.settings.json --records .\records.json
pwsh -NoProfile -File .\scripts\project-workflow.ps1 reconcile --desired .\desired.json --observed .\observed.json --supported-field Status
pwsh -NoProfile -File .\scripts\project-workflow.ps1 verify-traceability --trace .\trace.json --stage active
```

Standalone CLI reconciliation is preview-only. Live apply runs through the composed `project_management_reconcile` workflow tool and requires `apply=true` plus a non-empty idempotency key. The adapter preflights item revisions and searches the complete bounded Project inventory for an existing source issue or pull request before add. Conflicts, unsupported capabilities, inaccessible items, and incomplete pagination are reported without overwrite.

When enabled, platform composition adds:

- `project_management_inventory`;
- `project_management_reconcile`;
- `project_management_portfolio_status`;
- `project_management_persist_review`;
- `project_management_verify_traceability`.

Review evidence writes only beneath `.work/reviews/<review-id>/`, uses atomic replacement, retains staged recovery evidence on failed replacement, and exposes no delete operation. The reusable `.github/workflows/work-management.yml` validates the exact revision, settings, governance claims, focused P5 tests, and optionally the canonical verifier.

Historical commissioning evidence from 2026-08-07 proved standalone GitHub OAuth, private-repository read, and repository scoping before the runtime-lifecycle change. The then-approved user Project `#12` returned `404`; that stale work-management binding is no longer configured. Keep work management disabled until its own backend binding has a valid Project number and read-only inventory verification passes. Repository-local `gh_projects` entries constrain routing only; they do not prove Project existence or work-management commissioning. Fresh runtime-scoped OAuth evidence is a separate supervised commissioning check.

## Use Discover

`inspect_project` is exposed through local stdio and both HTTP instances. Supply one project directory beneath `C:\Projects`:

```json
{
  "path": "C:\\Projects\\example",
  "limits": {
    "max_files": 500,
    "max_output_chars": 200000
  }
}
```

Request limits are optional and may only narrow values in `settings.discover.limits`. The result contains versioned repository, evidence, local Git, verification-discovery, Python-structure, confidence, truncation, and handoff records. Verification declarations are evidence only: Discover does not execute repository code, tests, builds, or discovered commands.

`inspect_change` is exposed through the same transports for bounded inspection of the current working tree:

```json
{
  "path": "C:\\Projects\\example"
}
```

The public result preserves staged, unstaged, untracked, rename, copy, delete, type-change, and conflict path evidence retained by the bounded Git reader. It adds a deterministic change fingerprint, conventional file classifications, affected top-level scopes, impact counts, diagnostics, explicit unknowns, confidence, and truncation state. The public tool currently exposes only working-tree inspection. Internal contracts and services support staged, commit, range, and branch targets, context brokering, impact analysis, dependant evidence, affected tests, and verification handoffs, but those capabilities are not public tool parameters or operations on the current gateway. Pull-request and trusted remote evidence remain unavailable.

`DISCOVER_*` errors are structural and corrective. They are not HR policy decisions. Resolve the reported path, unsafe link/reparse condition, unsupported or excessive request limit, unreadable text, Git metadata condition, or configured budget rather than changing `policy/kis-mcp.policy.json`.

## Inspect provider runtime status

Call `kis_provider_status` to inspect the current Provider catalogue and runtime composition. For each approved external provider, read these fields separately:

- `registered` and `enabled` — descriptor and runtime selection state;
- `build_attempted`, `built`, `mounted`, and `state` — this process's composition result;
- `readiness` — provider-neutral local preflight and current runtime evidence;
- `user_status` — the current user-facing state and exact next action;
- `commissioning` — separate installation, configuration, authentication, upstream connection, tool discovery, and live-verification states.

Interpret the normal onboarding states as follows:

- **GitHub: `Ready — authentication required`** means the pinned executable, OAuth mode, provider configuration, and runtime-scoped client path are ready but the shared provider lifespan has not yet proved the current OAuth identity. Start `kis-op` and complete one supervised OAuth sign-in for that runtime.
- **GitHub: `Ready — authenticated`** means the current running provider lifespan completed `get_me` and initial upstream tool discovery successfully. Subsequent GitHub operations and long-tail discovery reuse that same provider process until `kis-op` stops. This is runtime evidence, not persistent authentication across restarts and not a claim that every GitHub operation was live-verified.
- **Supabase: `Ready — project initialization required`** means the commissioned provider is mounted with its local health surface but this repository is not yet linked to a Supabase project. Initialize or link a development/test project, set `SUPABASE_PROJECT_REF` in the supervised environment, then authenticate.
- **Supabase: `Ready — authentication required`** means project scope and local OAuth prerequisites are ready; browser authentication remains the next step.

A mounted provider is not automatically authenticated, upstream-connected, tool-discovered, or live verified. Reserve degraded, unavailable, or failed states for genuine local faults such as a missing executable, unavailable Windows credential storage, a legacy PAT conflict, invalid configuration, builder failure, mount failure, protocol failure, or runtime failure. `build_failed` with `RuntimeError` for GitHub indicates a local builder or settings failure, not a normal sign-in requirement. Do not add PATs, OAuth values, project references, or other secrets to repository JSON.

## Authenticate GitHub MCP

GitHub OAuth is owned by the running `kis-op` process. Ensure `GITHUB_PERSONAL_ACCESS_TOKEN` is unset; a PAT override is a configuration conflict and is never forwarded to the official GitHub MCP subprocess.

Start the operation runtime through the GitHub auth helper:

```powershell
pwsh -NoProfile -File .\scripts\auth-github-mcp.ps1
```

The helper validates the GitHub provider settings and repository-local settings, then starts `kis-op`. The provider-lifetime `get_me` call triggers the official browser OAuth flow once after the shared client connects. The launcher gives this supervised server/authentication phase its own 900-second default budget; `-AuthenticationTimeoutSeconds` may be set from 30 through 3600 seconds when needed. GitHub MCP stderr is drained continuously into the retained per-run server stderr log and echoed in the visible launcher, so browser/device-code fallback guidance remains visible while sign-in is pending. After the local MCP runtime becomes ready, the normal `-TimeoutSeconds` budget starts fresh for tunnel startup and readiness. Complete the sign-in and keep the `kis-op` runtime running; subsequent GitHub tool calls during the same runtime reuse the authenticated subprocess. Stopping or restarting `kis-op` discards the official provider's process-memory token and requires one new sign-in.

Run the focused non-live verification independently:

```powershell
pwsh -NoProfile -File .\scripts\smoke-github-mcp.ps1
```

This verifies the runtime client lifecycle, platform repository-selection wiring, GitHub routing/settings, scripts, and repository-settings contracts without claiming live authentication. Use `-RequireLive` only for an explicit supervised live commissioning check; it may require interactive OAuth and remains separate from repository verification.

## Configure and use the code-review agent

The gateway exposes one additive advisory operation:

```text
review_change_with_agent
```

It collects bounded local `AGENTS.md`, Git status, staged diff, and unstaged diff evidence for one repository beneath `C:\Projects`. It is advisory, exposes no mutation or nested-delegation operation, and instructs the selected backend not to edit, commit, merge, or spawn another agent.

The default backend order is defined in `settings/agents/code-review-agent.settings.json`:

```text
nvidia-nim -> codex-cli
```

For NVIDIA NIM, provide the key only in the supervised launcher process environment before starting kis-mcp:

```powershell
$SecureKey = Read-Host 'NVIDIA API key' -AsSecureString
$KeyPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureKey)
try {
    $env:NVIDIA_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($KeyPointer)
    pwsh -File .\scripts\start.ps1
}
finally {
    Remove-Item Env:NVIDIA_API_KEY -ErrorAction SilentlyContinue
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($KeyPointer)
}
```

Do not put the key in repository JSON, a command argument, logs, or an MCP request. NVIDIA calls use the configured OpenAI-compatible HTTPS chat-completions endpoint. The provider remains optional; a missing key reports unavailable/degraded readiness and permits fallback.

For Codex CLI, install and authenticate the `codex` executable through an explicit operator-supervised action outside normal Work, then keep the executable name or approved absolute location in the JSON settings. The gateway invokes only `scripts\invoke-codex-agent.ps1`, passes the review prompt through standard input, and requests:

```text
codex exec --ephemeral --json --sandbox read-only --color never -C <project> -
```

The read-only Codex sandbox request is defense in depth, not a replacement for operator supervision or OS-level containment. The wrapper fingerprints Git-visible repository state before and after the run, including HEAD, status, tracked diff, and untracked-file content hashes. If the fingerprint changes, the call fails with `CODEX_CLI_MUTATION_DETECTED`; it does not silently accept or automatically overwrite the detected change.

Example call:

```json
{
  "path": "C:\\Projects\\example",
  "instructions": "Prioritize correctness, error handling, and regressions.",
  "backend": null
}
```

Omit `backend` to use preferred/fallback order. Set it to `nvidia-nim` or `codex-cli` to require that backend without silently switching. Tests validate request shape, bounds, fallback, redaction, and additive registration; they do not prove live NVIDIA credentials or live Codex authentication.

## Run the KIS Control Center

The KIS Control Center is a separate read-only MCP App. It is not mounted into the primary gateway and does not participate in Work policy enforcement.

Run it from the source checkout through the locked project interpreter:

```powershell
C:\Projects\.kis-mcp\python-env\Scripts\python.exe -m kis_mcp.control_center
```

The server reads `settings\control-center.settings.json` and exposes:

- `open_kis_control_center` — a bounded structured local snapshot;
- `ui://kis-mcp/control-center.html` — a self-contained local MCP App resource.

The snapshot reports runtime identity, configured project and local Git state, the exact three-rule declaration, provider configuration with runtime-check requirements, bounded quarantine counts, verification guidance, and structural diagnostics. It performs no mutation or network access. Provider configuration does not prove provider authentication or commissioning, and verification remains unrecorded until current evidence is run.

## Commission Supabase OAuth

Use only a development or test Supabase project. The project-scoped provider exposes read/write capabilities even though commissioning invokes only a harmless read.

Set the project reference in the supervised operator environment and clear the legacy PAT variable:

```powershell
$env:SUPABASE_PROJECT_REF = '<development-project-ref>'
Remove-Item Env:SUPABASE_ACCESS_TOKEN -ErrorAction SilentlyContinue
```

Run the non-network OAuth preflight:

```powershell
pwsh -File .\scripts\smoke-supabase-mcp.ps1
```

Preflight validates schema version 2, mandatory project scope, Windows Credential Manager availability, and absence of the legacy PAT conflict. It does not contact Supabase or prove authentication.

Start explicit browser OAuth commissioning:

```powershell
pwsh -File .\scripts\auth-supabase-mcp.ps1
```

FastMCP performs OAuth discovery and dynamic client registration against the official project-scoped endpoint. Client and token state are persisted under the `kis-mcp/supabase` Windows Credential Manager service. The commissioning client lists the upstream surface and invokes only `get_project_url` with `{}`. It verifies that the returned project hostname matches the configured project reference without printing the project URL or project reference.

After authorization succeeds, prove persistent-token reuse and namespaced shared-runtime exposure:

```powershell
pwsh -File .\scripts\smoke-supabase-mcp.ps1 -SharedRuntime
```

The shared smoke requires Supabase to be mounted in `kis_provider_status` and invokes only `supabase_get_project_url`. `supabase_list_projects` must remain absent in project-scoped mode. Mutating tools may be discoverable but are not invoked.

Use `-Live` for a standalone authenticated recheck:

```powershell
pwsh -File .\scripts\smoke-supabase-mcp.ps1 -Live
```

Never set `SUPABASE_ACCESS_TOKEN`; PAT transport is intentionally unsupported. Never commit project references, access tokens, refresh tokens, client secrets, authorization codes, keyring values, or returned project URLs.

For recovery, stop provider processes, revoke the Supabase authorization when appropriate, remove the `kis-mcp/supabase` entries through Windows Credential Manager, rerun browser commissioning, and repeat the shared-runtime smoke.

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

The credential script prompts through `Read-Host -AsSecureString` and stores the value in the application-managed encrypted vault at the selected instance's non-secret `tunnel_secret_ref`. The setup script resolves that reference only through the secret-process boundary, exposes the value only through a temporary process-scoped environment reference for `tunnel-client init`, restores the prior process environment in `finally`, and writes generated profiles only beneath `C:\Projects\.kis-mcp\tunnel-client\profiles`.

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
- reclaims a selected-instance listener or orphan process tree only when the canonical executable, instance, profile, and endpoint identity match; an unrelated listener fails with PID/process diagnostics and is never terminated;
- enforces the external canonical Python environment and moves repository-local `.venv` or `.pytest_cache` transients into recoverable quarantine before startup;
- starts the selected remote runtime on `127.0.0.1:8010` for `kis-op` or `127.0.0.1:8011` for `kis-dev`;
- gives server startup and supervised provider authentication a separate 900-second default budget and echoes retained server stderr live so OAuth/device-code guidance remains visible;
- proves MCP initialization and proves the new selected server process owns that exact listener before readiness;
- starts a fresh machine/tunnel readiness deadline only after the server/authentication phase has completed;
- writes one per-instance `current.json` ownership record while retaining timestamped startup/log evidence;
- starts only the selected tunnel profile and tunnel ID;
- waits for the selected tunnel client's loopback `/readyz` endpoint within the normal `TimeoutSeconds` budget;
- writes per-instance startup state and logs beneath the selected runtime directory;
- owns and cleans up only the server and tunnel processes created by that launcher invocation.

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

## Parallel change worktrees

Create implementation worktrees only from a clean primary `main` checkout. The workflow supports any number of parallel agents; it rejects duplicate outcomes and conflicting scope claims rather than imposing a concurrency limit.

Create a change:

```powershell
pwsh -File .\scripts\change-workflow.ps1 new 002-example-change `
    --outcome "Implement one bounded result" `
    --owned "src/example/**" `
    --owned "tests/test_example.py" `
    --exclude "policy/**"
```

The command creates branch `change/002-example-change`, worktree `.work/worktrees/002-example-change`, and the five required artifacts beneath `.work/changes/<change-id>/`.

List or validate active claims:

```powershell
pwsh -File .\scripts\change-workflow.ps1 list
pwsh -File .\scripts\change-workflow.ps1 validate
```

Before committing or requesting review, run the scope check from the change worktree:

```powershell
pwsh -File .\scripts\change-workflow.ps1 check
```

The check compares committed, staged, unstaged, and untracked paths with `owned_paths`, `shared_paths`, and `excluded_paths`. Exact paths and recursive `/**` claims are supported; other glob forms are rejected.

After the branch is merged into its declared base, return to the clean primary checkout and run:

```powershell
pwsh -File .\scripts\change-workflow.ps1 cleanup 002-example-change
```

Cleanup refuses a dirty worktree or an unmerged branch. It performs only normal `git worktree remove`, `git branch -d`, and `git worktree prune` operations; it never forces deletion.

## Verify

Run:

```powershell
pwsh -File .\scripts\verify.ps1
```

Verification requires `uv.lock`, synchronizes the external Python environment offline with `--frozen`, and invokes `scripts\verify.py` through that environment's exact Python executable. The Python verifier confirms the interpreter location, FastMCP 3.4.4, pytest `>=8.4,<9`, Python syntax, configuration, and the full test suite.

The repository checks also confirm:

1. the policy contains exactly HR-001, HR-002, and HR-003;
2. repository-local skills are not used as the runtime catalogue and every shared runtime Skill has reviewed capability metadata;
3. Desktop Commander is not vendored;
4. generated-state paths remain canonical and outside the repository;
5. predecessor runtime identities are absent from authoritative and runtime files;
6. path, exact network-target, allowed negative-case, quarantine, provider-readiness, exposed-schema, middleware, modular-boundary, and provider-contract regression tests pass;
7. Discover contracts, JSON settings, path identity, link/reparse and hard-link handling, traversal budgets, deterministic detection, fixed local Git reads, pure Python AST indexing, output compaction, evidence integrity, donor independence, architecture boundaries, and tool registration pass;
8. provider runtime settings/schema validation, deterministic namespaced mounting, disabled/unregistered behavior, builder and mount failure containment, status redaction, parent-middleware routing, and instance-scoped composition pass;
9. capability settings/schema validation, complete contributions, readiness containment, hard eligibility before scoring, deterministic explainable ranking, bounded direct exposure, status-only suppression, original-schema long-tail dispatch, workflow metadata, and architecture boundaries pass;
10. code-review agent settings/schema validation, NVIDIA NIM request and response handling, Codex fixed-script invocation, bounded evidence, fallback behavior, redaction, and additive registration pass.

Verification also checks the pinned provider surface under `contracts/desktop-commander/`, including provider identity, all exposed tool schemas and annotations, effect classification coverage, adapter mappings, and the recorded SHA-256 fingerprint. These checks are release evidence only; they do not add a runtime allowlist or a fourth policy rule.

Verification improves confidence in resolved intent and boundary behavior. It does not create a separate permission gate and does not replace live provider end-to-end testing.

## Upgrade Desktop Commander

1. Check the authoritative package release outside Work.
2. Update only `desktop_commander.version` in `settings/kis-mcp.settings.json`.
3. Run the operator installation script.
4. Capture the installed provider contract through local stdio:

   ```powershell
   pwsh -File .\scripts\capture-provider-contract.ps1
   ```

5. Review the resulting contract and fingerprint diff, including every changed tool, argument, annotation, and effect classification.
6. Update only the narrow adapter mappings that changed.
7. Run the complete verification suite.
8. Record the verified version in the implementation-status documentation.

Do not use `latest` during normal startup.

## Quarantine and restore

Quarantine records are stored beneath the configured quarantine root. Each operation has a unique ID, intact payload, and restoration metadata.

Restore only when the original path is absent. A restore operation fails rather than overwrites.

Permanent disposal is intentionally not exposed as a normal Work tool.

## Troubleshooting

- `KIS_MCP_REMOTE_INSTANCE_NOT_CONFIGURED`: enter the real tunnel ID for the selected instance, set `configured` to `true`, and store its credential before setup or startup.
- A missing vault entry for the selected tunnel reference: run `scripts\set-tunnel-credential.ps1` for that instance, then retry.
- `KIS_MCP_TUNNEL_SECRET_REFERENCE_MISSING` or `KIS_MCP_TUNNEL_SECRET_REFERENCE_INVALID`: restore the selected instance's canonical non-secret `tunnel_secret_ref` in JSON.
- `KIS_MCP_TUNNEL_CLIENT_MISSING`: restore the executable at the settings-defined `C:\Tools\openai-tunnel-client\tunnel-client.exe` path or correct the JSON setting.
- `KIS_MCP_TUNNEL_PROFILE_EXISTS`: rerun setup with `-BackupExistingProfile` only when replacement is intended.
- `KIS_MCP_TUNNEL_PROFILE_INVALID`: inspect the tunnel-client doctor output; do not start the profile until all checks pass.
- `KIS_MCP_TUNNEL_PROFILE_MISSING`: run `scripts\setup-tunnel.ps1` for the selected instance.
- `KIS_MCP_AUTHENTICATION_TIMEOUT_INVALID`: set `AuthenticationTimeoutSeconds` from 30 through 3600 seconds; the default is 900 seconds and is independent from tunnel readiness timing.
- `KIS_MCP_PORT_OWNED_BY_OTHER_PROCESS`: the selected instance port belongs to a process that does not match the selected KIS runtime identity; inspect the reported PID/process and stop or reconfigure it explicitly. The launcher will not terminate it.
- `KIS_MCP_STALE_PORT_NOT_RELEASED`: a positively identified stale selected-instance runtime did not release its configured port after reclamation; inspect that instance's process tree before retrying.
- `KIS_MCP_ENDPOINT_OWNER_INVALID` or `KIS_MCP_ENDPOINT_OWNER_STALE`: the newly started selected runtime answered incorrectly or does not own the configured listener; startup cleans up its owned process tree rather than declaring readiness.
- `KIS_MCP_SMOKE_PORT_IN_USE`: stop the listener used by the temporary smoke endpoint or choose the intended smoke instance.
- `KIS_MCP_HTTP_NOT_READY` or `KIS_MCP_SMOKE_INITIALIZE_FAILED`: inspect Desktop Commander readiness, the Python environment, and the selected loopback endpoint.
- `KIS_MCP_TUNNEL_NOT_READY`: inspect tunnel-client output, the configured tunnel association, runtime key, and control-plane scope.
- `KIS_MCP_SMOKE_TOOLS_MISSING`: stop commissioning; the remote catalogue is reduced or the provider contract changed.
- `KIS_MCP_SMOKE_NETWORK_ONLY_TOOL_EXPOSED`: stop commissioning; the proven network-only feedback tool must not be exposed.
- `KIS_MCP_SMOKE_DISCOVER_CALL_FAILED`: inspect the `inspect_project` tool result, repository path, Discover settings, and configured budgets before retrying.
- `KIS_MCP_SMOKE_WRITE_CALL_FAILED`, `KIS_MCP_SMOKE_READ_CALL_FAILED`, or `KIS_MCP_SMOKE_QUARANTINE_CALL_FAILED`: inspect the corresponding MCP tool result and quarantine state before retrying.

- `DESKTOP_COMMANDER_ARCHIVE_NOT_FOUND`: place the configured scanned `.tgz` in the current user's `Downloads` directory.
- `DESKTOP_COMMANDER_ARCHIVE_HASH_MISMATCH`: stop; the archive differs from the recorded scanned digest.
- `DESKTOP_COMMANDER_OFFLINE_INSTALL_FAILED`: the scanned project-local npm cache does not contain the complete runtime dependency closure; run `prepare-desktop-commander-cache.ps1`, then retry without enabling registry fallback.
- `DESKTOP_COMMANDER_DEPENDENCY_ACQUISITION_FAILED`: the supervised dependency download failed; inspect the retained acquisition directory and npm log before retrying.
- `DESKTOP_COMMANDER_DEPENDENCY_SCAN_FAILED`: Defender did not return a clean result; nothing was promoted. Keep the acquisition tree isolated for operator review.
- `DESKTOP_COMMANDER_CACHE_PROMOTION_FAILED`: cache activation failed; the prior cache is restored when possible and the clean acquisition tree remains recoverable.

- `DESKTOP_COMMANDER_NOT_INSTALLED`: run the supervised install script outside Work.
- `POLICY_RULE_SET_INVALID`: restore the exact three-rule JSON file.
- `HR-001_WRITE_OUTSIDE_PROJECTS`: choose a destination beneath `C:\Projects`.
- `HR-002_EXTERNAL_NETWORK`: remove the concrete external target, use an approved connector, or use an explicit operator action outside Work.
- `UNSUPPORTED_PROVIDER_TOOL` or `UNSUPPORTED_PROVIDER_MODE`: use the exposed local provider contract; the named external-only provider surface is not part of Work.
- `PROVIDER_CONFIGURATION_INVARIANT`: leave Desktop Commander's provider-native restriction fields gateway-managed and empty.
- `INVALID_INVOCATION_PATH`: provide a concrete path that can be resolved and safely transformed.
- `HR-003_QUARANTINE_REQUIRED`: allow the gateway to move the target to quarantine rather than delete it.
- `HR-003_QUARANTINE_FAILED`: inspect quarantine availability and retry without permanent deletion.
