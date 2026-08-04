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

## Configure

Edit only the canonical JSON files:

- `settings/kis-mcp.settings.json` for identity, paths, Desktop Commander version and launch settings, Discover retrieval settings, local stdio transport, ChatGPT remote transport, and informational implementation status.
- `settings/providers/platform-runtime.provider.json` for the exact approved external provider IDs, runtime enablement, and unique lower-case namespaces. Do not place credentials in this file.
- `policy/kis-mcp.policy.json` for the exact three-rule declaration.

The policy file must contain exactly HR-001, HR-002, and HR-003. Adding, removing, or weakening a rule requires explicit operator approval.

The normal approved boundary is `C:\Projects`. State and quarantine roots must remain true descendants of it.

`settings.discover` owns all Discover retrieval behavior: enablement, exclusions, allowed text extensions and conventional filenames, encodings, hard-link handling, and file, directory, byte, depth, traversal-time, Git, Python-index, evidence, and output budgets. Change those values in JSON rather than hard-coding new limits or exclusions. Request-side limits may only narrow configured maxima.

`settings.remote_mcp` contains two named instances:

- `operation` — the normal ChatGPT-facing tool instance;
- `development` — the isolated commissioning and change-validation instance.

Each instance has its own loopback port, tunnel profile, explicit `configured` state, non-secret `tunnel_id`, and non-secret `tunnel_credential_target`. The target names a per-user Generic Credential in Windows Credential Manager; the secret is not stored in JSON or generated state. The tunnel executable is read only from:

```text
C:\Tools\openai-tunnel-client\tunnel-client.exe
```

The checked-in instance records remain `configured: false` with blank tunnel IDs until commissioning. Before tunnel setup, populate the real `tunnel_id`, change `configured` to `true`, and store the secret once with `scripts\set-tunnel-credential.ps1` for that instance's configured credential target. Do not commit credential values or generated profile YAML.

`active_instance` controls the default only. Use `-Instance operation` or `-Instance development` for an explicit switch. There is no automatic failover.

Configuration, instance selection, catalogue metadata, profiles, and status fields do not disable otherwise permitted Desktop Commander tools. Both instances expose the same mixed-purpose tool surface and apply only HR-001, HR-002, and HR-003 to concrete invocations.

## Start local stdio
Run:

```powershell
pwsh -File .\scripts\start.ps1
```

Startup does not install or update packages. It requires the external locked Python environment and the pinned Desktop Commander entry point to exist, validates the exact three-rule set and canonical state paths, validates provider offline readiness, and then starts `kis-mcp` over stdio using `C:\Projects\.kis-mcp\python-env\Scripts\python.exe`.

Provider readiness rejects enabled telemetry, a missing or non-loopback feature-flag URL, and missing local Chrome when configured as required because the pinned provider source proves those states cause automatic external activity. It also requires Desktop Commander's persisted `blockedCommands` and `allowedDirectories` fields to remain empty so the provider cannot add independent command or directory restrictions beneath FastMCP.

After the core gateway is created, startup loads the strict provider-runtime JSON and attempts enabled GitHub and Supabase adapter builds in stable provider-ID order. Successful adapters mount as `github_*` and `supabase_*`. Missing binaries, credentials, invalid builder results, or mount failures are recorded by type and do not prevent the Work, Discover, Skills, or gateway surfaces from starting. Invalid runtime JSON remains a startup configuration error.

The feedback tool and `read_file.isUrl` mode are absent from the exposed Work contract. Terminal and process tools remain available; the gateway blocks or transforms only concrete HR-001, HR-002, or HR-003 effects.

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

The result preserves staged, unstaged, untracked, rename, copy, delete, type-change, and conflict path evidence retained by the bounded Git reader. It adds a deterministic change fingerprint, conventional file classifications, affected top-level scopes, impact counts, diagnostics, explicit unknowns, confidence, and truncation state. It does not inspect commits, ranges, branches, pull requests, remote checks, changed symbols, dependant modules, or verification handoffs.

`DISCOVER_*` errors are structural and corrective. They are not HR policy decisions. Resolve the reported path, unsafe link/reparse condition, unsupported or excessive request limit, unreadable text, Git metadata condition, or configured budget rather than changing `policy/kis-mcp.policy.json`.

## Inspect provider runtime status

Call `kis_provider_status` to inspect the current Provider catalogue and runtime composition. For each approved external provider, read these fields separately:

- `registered` and `enabled` — descriptor and runtime selection state;
- `build_attempted`, `built`, `mounted`, and `state` — this process's composition result;
- `readiness` — provider-neutral local preflight evidence;
- `commissioning` — installation, configuration, authentication, upstream connection, tool discovery, and live verification. These remain `not_verified` until dedicated authenticated commissioning proves them.

`build_failed` with `RuntimeError` for GitHub indicates a local builder or settings failure; inspect the provider's offline readiness details to distinguish a missing executable from invalid configuration or other preflight failures. A mounted provider is not automatically authenticated or live verified. GitHub uses its supervised OAuth commissioning workflow. Supabase uses hosted OAuth/DCR with Windows Credential Manager persistence and requires the explicit commissioning commands below. Do not add PATs, OAuth values, project references, or other secrets to repository JSON.

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

FastMCP performs OAuth discovery and dynamic client registration against the official project-scoped endpoint. Client and token state are persisted under the `kis-mcp/supabase` Windows Credential Manager service. The commissioning client lists the upstream surface and invokes only `get_project_url` with `{}`. It verifies the returned project hostname without printing the project URL or project reference.

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

1. Enter its real `tunnel_id` in `settings.remote_mcp.instances`.
2. Set that instance's `configured` field to `true`.
3. Store the tunnel secret once in Windows Credential Manager.
4. Create the project-local tunnel profile.

```powershell
pwsh -File .\scripts\set-tunnel-credential.ps1 -Instance development
pwsh -File .\scripts\setup-tunnel.ps1 -Instance development
```

The credential script prompts through `Read-Host -AsSecureString` and stores a per-user Generic Credential at the non-secret `tunnel_credential_target` declared in JSON. The setup script retrieves that credential, exposes it only through a temporary process-scoped environment reference for `tunnel-client init`, restores the prior process environment in `finally`, and writes generated profiles only beneath `C:\Projects\.kis-mcp\tunnel-client\profiles`.

The setup script reads the tunnel client path, profile name, tunnel ID, local MCP URL, and credential target from JSON. It refuses to replace an existing profile unless `-BackupExistingProfile` is supplied; replacement first moves the old YAML profile into a timestamped backup. The Windows credential is not copied into profile backups or repository files.

Configure the operation profile separately:

```powershell
pwsh -File .\scripts\set-tunnel-credential.ps1 -Instance operation
pwsh -File .\scripts\setup-tunnel.ps1 -Instance operation
```

The two profiles, tunnel IDs, and credential targets must remain distinct. Do not point both instances at one tunnel record.

## Start the ChatGPT-facing instance
Start the development instance during commissioning:

```powershell
pwsh -File .\scripts\start-chatgpt.ps1 -Instance development
```

Start the operational instance after commissioning:

```powershell
pwsh -File .\scripts\start-chatgpt.ps1 -Instance operation
```

Omit `-Instance` to use `settings.remote_mcp.active_instance`. The launcher retrieves the selected instance's tunnel secret from Windows Credential Manager, passes it only in the owned tunnel process environment, and clears the temporary PowerShell value after process creation. It then:

- validates the selected instance, tunnel ID, configured state, credential target, profile, and local prerequisites;
- refuses startup while the other ChatGPT-facing instance is listening, enforcing explicit switch-over;
- starts `python -m kis_mcp.remote_runtime` on its loopback port;
- proves MCP initialization locally;
- retrieves the stored Windows credential immediately before creating the owned tunnel process;
- starts the configured tunnel profile against the exact local `/mcp` URL;
- waits for the tunnel client's loopback `/readyz` endpoint;
- owns both processes and stops the peer process when either exits.

Keep the launcher window open while ChatGPT uses the tool.

## Create or switch the ChatGPT app

In ChatGPT developer-mode app settings, create a custom app using the Secure MCP Tunnel connection. Select the available tunnel or paste the instance's configured tunnel ID, then scan the tools. Confirm that the scanned catalogue includes representative filesystem, editing, terminal/process, and gateway operations. Do not accept a reduced profile-based catalogue.

The tunnel must be associated with the same ChatGPT workspace or organization that will use the app. Keep separate custom apps or explicit app configurations for `operation` and `development`; switch by stopping one launcher and starting the other, then selecting the corresponding ChatGPT app. Do not run both against the same tunnel identity.

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

The command creates branch `change/002-example-change`, worktree `.work/worktrees/002-example-change`, and the five required artifacts beneath `.work/changes/002-example-change/`.

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
2. repository skills are not referenced by runtime or configuration;
3. Desktop Commander is not vendored;
4. generated-state paths remain canonical and outside the repository;
5. predecessor runtime identities are absent from authoritative and runtime files;
6. path, exact network-target, allowed negative-case, quarantine, provider-readiness, exposed-schema, middleware, modular-boundary, and provider-contract regression tests pass;
7. Discover contracts, JSON settings, path identity, link/reparse and hard-link handling, traversal budgets, deterministic detection, fixed local Git reads, pure Python AST indexing, output compaction, evidence integrity, donor independence, architecture boundaries, and tool registration pass;
8. provider runtime settings/schema validation, deterministic namespaced mounting, disabled/unregistered behavior, builder and mount failure containment, status redaction, parent-middleware routing, and additive public-tool registration pass.

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

- `KIS_MCP_OTHER_INSTANCE_ACTIVE`: stop the other ChatGPT-facing launcher before switching instances.

- `KIS_MCP_REMOTE_INSTANCE_NOT_CONFIGURED`: enter the real tunnel ID for the selected instance, set `configured` to `true`, and store its credential before setup or startup.
- `KIS_MCP_TUNNEL_CREDENTIAL_MISSING`: run `scripts\set-tunnel-credential.ps1` for the selected instance.
- `KIS_MCP_TUNNEL_CREDENTIAL_TARGET_MISSING` or `KIS_MCP_TUNNEL_CREDENTIAL_TARGET_INVALID`: restore the non-secret `tunnel_credential_target` in canonical JSON.
- `KIS_MCP_TUNNEL_CLIENT_MISSING`: restore the executable at the settings-defined `C:\Tools\openai-tunnel-client\tunnel-client.exe` path or correct the JSON setting.
- `KIS_MCP_TUNNEL_PROFILE_EXISTS`: rerun setup with `-BackupExistingProfile` only when replacement is intended.
- `KIS_MCP_TUNNEL_PROFILE_INVALID`: inspect the tunnel-client doctor output; do not start the profile until all checks pass.
- `KIS_MCP_TUNNEL_PROFILE_MISSING`: run `scripts\setup-tunnel.ps1` for the selected instance.
- `KIS_MCP_PORT_IN_USE` or `KIS_MCP_SMOKE_PORT_IN_USE`: stop the existing listener or correct the instance port in settings.
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
