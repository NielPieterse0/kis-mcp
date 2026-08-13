# Operations

## Authority boundary

This document is the canonical operator runbook for installation, configuration, startup, commissioning, verification, troubleshooting, and recovery. Repository workflow and documentation routing belong to [`../AGENTS.md`](../AGENTS.md); current architecture and implementation status belong to [`../SPEC.md`](../SPEC.md); trust semantics belong to [`TRUST-MODEL.md`](TRUST-MODEL.md); target architecture belongs to [`PLATFORM-CONCEPT.md`](PLATFORM-CONCEPT.md). This runbook references those owners rather than redefining their doctrine.

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

Generated state remains inside the approved write boundary. The normal state root is outside the repository; the operator-approved agnix native runtime is the one compatibility exception and lives in the ignored repo-local `.temp` tree:

```text
C:\Projects\.kis-mcp\
├── .claude-server-commander\
├── desktop-commander\
├── context7\
├── serena\
├── discover\
│   └── projects\<project-id>\<worktree-fingerprint>\
├── commissioning\
├── tools\
│   └── agentsys\6.0.1\
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

Agnix runtime compatibility state is separate and ignored:

```text
C:\Projects\kis-mcp\.temp\tools\agnix\0.45.0\
```

Do not commit generated state, including the repo-local agnix runtime. Repository-local `.venv`, `.pytest_cache`, PowerShell module cache, provider state, or command-state directories are not authoritative project artifacts.

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

agnix `0.45.0` is installed at `C:\Projects\kis-mcp\.temp\tools\agnix\0.45.0` because the same native executable was blocked by Windows Application Control from the prior central tools path but executes successfully from this operator-approved ignored repo-local compatibility path. KIS exposes only `validate_agent_configuration(project, target, strict, max_files)`, which invokes the pinned native binary with fixed JSON-validation arguments through normal Work middleware. It exposes no `--fix`, watch, init, telemetry, schema, tools, arbitrary-command, or MCP passthrough authority. The npm distribution still does not include the separate native `agnix-mcp` binary, so general MCP mounting remains deferred.

See [`development/bootstrap/agentsys.md`](development/bootstrap/agentsys.md) and [`development/bootstrap/agnix.md`](development/bootstrap/agnix.md) for exact managed paths, catalogue counts, launch prerequisites, and recovery.

## Configure

Edit only the canonical JSON files:

- `settings/kis-mcp.settings.json` for identity, paths, Desktop Commander version and launch settings, Discover retrieval settings, local stdio transport, ChatGPT remote transport, and informational implementation status.
- `settings/providers/platform-runtime.provider.json` for the exact approved mounted MCP provider IDs, runtime enablement, and unique lower-case namespaces. Do not place credentials in this file.
- `settings/providers/context7.provider.json` for the pinned local Context7 MCP package/entry point and independent external-documentation connector contract.
- `settings/providers/dbhub.provider.json` for the exact DBHub source/release identity, stdio entry point, generated runtime root, row bound, and enabled read-only tools. Do not store DSNs or credential references here.
- `settings/providers/dockerhub.provider.json` for the exact official Docker Hub source revision, stdio entry point, and public/PAT metadata. Public mode stores no secret; PAT mode stores only username plus a canonical vault reference.
- `settings/providers/serena.provider.json` for the pinned Serena 1.6.1 installation, contained provider state, relocatable venv-interpreter launch, and the central per-project state root. Normal runtime forces `UV_OFFLINE=1`; KIS configures Serena's `project_serena_folder_location` as `C:\\Projects\\.kis-mcp\\serena\\projects\\$projectFolderName\\.serena`, pre-creates that path, and refuses same-folder-name collisions across different project roots. Do not replace it with the promoted `serena.exe` console launcher, allow language-server package acquisition, or permit repo-local `.serena` state.
- `settings/providers/github-mcp.provider.json` for GitHub provider identity, pinned source/executable, OAuth mode, PAT-conflict metadata, and toolsets only. Do not place repository or Project routing in provider authentication settings.
- `settings/projects.settings.json` for the strict central project registry: stable project IDs, absolute local roots, and optional GitHub repository, GitHub Project, Supabase, database, and Docker Hub routing. Local database locations are project-relative SQLite paths; external database bindings carry only canonical vault references; Docker Hub project bindings carry only namespaces. Store no credential values here.
- `settings/work-management/github-projects.settings.json` for Work Management feature/gate/automation/evidence modes and stable backend bindings, and `settings/work-management/github-project-schema.json` for the desired 18-field/12-view Project projection used by schema-drift checks.
- `settings.github_cli.config_dir` for the non-secret GitHub CLI authentication-state directory used by KIS exact registered-repository mutations. It must stay beneath `C:\\Projects`, outside the repository, and is supplied only as process-scoped `GH_CONFIG_DIR`; do not place tokens in repository JSON.
- `settings/kis-repository.settings.json` only for legacy repository-settings compatibility callers; normal gateway routing is registry-backed.
- `settings/agents/code-review-agent.settings.json` for the one advisory code-review agent, NVIDIA NIM and Codex CLI backend configuration, preferred/fallback order, and evidence/output budgets. Store only the `NVIDIA_API_KEY` environment-variable name, never the API key value.
- `settings/capabilities.settings.json` for suitability and intrinsic-quality weights, the bounded direct profile, discovery operations, readiness penalty, and reviewed capability metadata for every current shared Skill.
- `policy/kis-mcp.policy.json` for the exact three-rule declaration.

The policy file must contain exactly HR-001, HR-002, and HR-003. Adding, removing, or weakening a rule requires explicit operator approval.

The normal approved boundary is `C:\Projects`. State and quarantine roots must remain true descendants of it.

Tracked text line endings are governed by the target worktree's effective Git attributes. The repository baseline declares LF for normal text and explicit CRLF exceptions in `.gitattributes`. KIS normalizes newline-bearing `write_file` and `edit_block` arguments to Git's resolved `eol` before Desktop Commander writes them, skips paths Git marks `text=unset`, and leaves unresolved/non-Git paths unchanged. Do not disable `core.safecrlf` or apply blanket LF conversion to explicit CRLF/binary paths to work around staging errors.

`settings.discover` owns all Discover retrieval and persistent-intelligence behavior: enablement, exclusions, allowed text extensions and conventional filenames, encodings, hard-link handling, file/directory/Git/index/evidence/output budgets, plus the project-memory state root, schema version, maximum stored bytes/files/modules/symbols/relationships, fingerprint fields, provider inclusion, corruption handling, and recoverable supersession behavior. The default memory root is `C:\Projects\.kis-mcp\discover`. Change those values in JSON rather than hard-coding new limits or exclusions. Request-side limits may only narrow configured maxima. Persisted generations are derived evidence and never override newer repository, Git, documentation, contract, or registered-project evidence.

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

After the core gateway is created, startup loads the strict provider-runtime JSON and attempts the seven enabled Context7, Control Center, DBHub, Docker Hub MCP, GitHub, Serena, and Supabase adapter builds in stable provider-ID order. Successful adapters mount under `context7_*`, `controlcenter_*`, `db_*`, `dockerhub_*`, `github_*`, `serena_*`, and `supabase_*`. Context7 exposes only its pinned external documentation reads. DBHub creates one isolated read-only child per registered database binding and preserves stable KIS project/binding operation names; Docker Hub is an external registry connector and does not replace local Docker Engine/process capability. Serena mounts only `get_symbols_overview`, `find_symbol`, and `find_referencing_symbols`; project activation is internal, mutation/memory tools are hidden, provider state remains beneath `C:\Projects\.kis-mcp\serena`, and `UV_OFFLINE=1` prevents language-server acquisition. Before Serena activation, KIS reconciles its global `project_serena_folder_location` to the JSON-governed central template, creates the corresponding central project folder, and verifies a `project-root.json` identity marker so two different same-name roots cannot share state. A repo-local `.serena` directory is therefore neither required nor expected. Discover shares that Serena runtime when ready and otherwise uses deterministic local parsers. NVIDIA NIM is registered in the Provider catalogue but is consumed only by the advisory agent rather than mounted as a general provider passthrough. Codex CLI is a local Tool-registry adapter behind the same agent. Missing binaries, credentials, invalid builder results, transport failures, or mount failures do not prevent the Work, deterministic Discover, Skills, agent-registration, or gateway surfaces from starting. Invalid provider-runtime JSON remains a startup configuration error. Missing or invalid agent JSON disables only the optional code-review agent and its NVIDIA/Codex backends.

For GitHub, the Provider runtime creates one shared FastMCP client and keeps its upstream GitHub MCP subprocess connected for the lifetime of the parent `kis-op` process. Before the mounted provider lifespan starts, aggregate tool inspection exposes only the GitHub adapter's local surface and deliberately does not connect the upstream GitHub process. After the shared client connects, a single `get_me` startup call triggers OAuth and initial upstream tool discovery publishes the current runtime tool snapshot without closing that connection. Downstream tool sessions reuse the authenticated process; stopping or restarting `kis-op` closes it and requires one new sign-in on the next start. Repository and Project authorization are evaluated independently on every call against the GitHub repository/Project union in `settings/projects.settings.json`.

For Supabase, the runtime uses the same persistent client seam without a provider-specific startup call. It connects once to `https://mcp.supabase.com/mcp`, performs account OAuth, discovers the upstream tool surface, and reuses that client until the parent KIS runtime stops. `SUPABASE_PROJECT_REF` is not a startup requirement. Project-targeted calls must carry an explicit registered Supabase `project_id`; targetless calls are accepted only when the discovered upstream tool declares itself read-only.

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

Dispatch normally re-enters the original FastMCP tool with `run_middleware=True`; original schemas remain authoritative and a generic parameters object does not weaken validation. The external dispatcher refuses ordinary approval-gated operations. The only virtual exception is the KIS-owned `registered-github` family, whose strict schemas require `approved=true` and whose implementation independently enforces registered targets plus exact remote-state preconditions and verification. Unavailable, disabled, authentication-gated, build-failed, and mount-failed operations remain visible in status and catalogue results but are not dispatched.

For registered repositories, `kis_github_publish_registered_commit` publishes one existing immutable local commit to a named branch only when the observed remote ref exactly matches `expected_remote_base` (or is absent when that value is null), then verifies the remote ref equals the exact local commit SHA. When local merge history is not an ancestor of current GitHub history but the declared local source-base tree is exactly identical to the expected remote-default tree, `kis_github_reconcile_registered_commit` can instead create a non-default review-branch commit that preserves the exact source tree and uses the verified remote-default SHA as its sole parent. `kis_github_create_registered_pull_request` verifies exact head/base state before and after creation. `kis_github_configure_registered_repository` configures one registered repository for merge commits only, disables squash/rebase landing, keeps GitHub automatic branch deletion disabled, and verifies those settings after mutation. `kis_github_merge_registered_pull_request` accepts only `merge` and merges only the explicitly approved pull-request head with `--match-head-commit`; `kis_github_delete_registered_branch` refuses the default branch and deletes only an exact expected head with a ref lease. These operations do not expose arbitrary `gh`, shell, commit messages, force-rewrite, admin-bypass, or token access.

`prepare_reviewable_pull_request` is the bounded completion coordinator for the pre-review phase. Supply a registered `project_id`, exact local `commit` and `source_base` SHAs, a non-default review branch with its exact expected remote SHA/absence, the exact expected remote-default SHA, PR outcome/summary, explicit approval, the `lean|standard|rigorous` risk profile, documentation impact, residual state, and optional verification/review overrides. KIS runs `execute_change_workflow` against that exact source commit using the risk-scaled defaults unless overrides are supplied. Only a `passed` result permits external mutation. KIS then reconciles the exact tree, generates deterministic PR metadata containing risk/scope/source+published heads/verification/review/documentation/residual state, creates the PR only at the returned reconciled head, and returns both source and published SHAs. It deliberately stops with an open reviewable PR; provider-native GitHub Actions evidence for that PR head is the final merge-verification gate.

Tool quality and suitability scores are recommendation evidence only. They never authorize a call, override HR-001, HR-002, or HR-003, or replace provider authentication and commissioning.

## Configure work management

Work management uses `settings/work-management/github-projects.settings.json` for behavior and `settings/projects.settings.json` for managed-project identity and GitHub Project routing coordinates. It projects governed local changes and Git/GitHub lifecycle facts; it is not required to establish local change authority. The checked-in `kis-mcp` binding is enabled. Before changing or adding a managed project:

1. register its stable ID, local root, GitHub repository, and intended GitHub Project coordinate in the central project registry;
2. keep the existing work-management backend-binding ID stable unless a separate compatibility migration is approved;
3. start `kis-op` and complete the one supervised GitHub OAuth sign-in required for that runtime;
4. run settings validation and a read-only inventory check;
5. review reconciliation previews before any apply operation.

If the work-management project identity conflicts with the central registry, loading fails closed. Feature modes, automation, gates, and evidence budgets remain owned by the work-management settings file.

Use the fixed-shape CLI:

```powershell
pwsh -NoProfile -File .\scripts\project-workflow.ps1 settings --settings settings\work-management\github-projects.settings.json
pwsh -NoProfile -File .\scripts\project-workflow.ps1 schema-manifest --manifest settings\work-management\github-project-schema.json
pwsh -NoProfile -File .\scripts\project-workflow.ps1 status --settings settings\work-management\github-projects.settings.json --records .\records.json
pwsh -NoProfile -File .\scripts\project-workflow.ps1 reconcile --desired .\desired.json --observed .\observed.json --supported-field Status
pwsh -NoProfile -File .\scripts\project-workflow.ps1 verify-traceability --trace .\trace.json --stage active
pwsh -NoProfile -File .\scripts\project-workflow.ps1 merge-readiness --record .\record.json --trace .\trace.json --pull-request-number 123
```

Standalone CLI reconciliation is preview-only. Live apply runs through `project_management_reconcile` and requires `apply=true` plus a non-empty idempotency key. The adapter preflights item revisions and searches the complete bounded Project inventory for an existing source issue or pull request before add. Conflicts, unsupported capabilities, inaccessible items, and incomplete pagination are reported without overwrite.

When enabled, platform composition adds eight bounded task-level operations:

- `project_management_inventory`;
- `project_management_reconcile`;
- `project_management_schema_status`;
- `project_management_merge_readiness`;
- `project_management_documentation_reconcile`;
- `project_management_portfolio_status`;
- `project_management_persist_review`;
- `project_management_verify_traceability`.

Use `project_management_schema_status` before schema-dependent reconciliation. It reads the live field surface and compares it with `settings/work-management/github-project-schema.json`, whose target remains **18 core fields and 12 named views**. Provider middleware permits Project/field/item/status-update reads and bounded `update_project_items` batches, while Project/item deletion, Project creation, status-update creation, iteration-field creation, generic custom-field creation, saved-view creation, and unrestricted GraphQL remain outside the approved mutation surface. Report those provisioning gaps rather than bypassing the boundary.

For managed implementation/specification work, classify documentation impact when the Work projection is created or reconciled. `project_management_merge_readiness` combines the projection with exact PR/head evidence and requires a passing provider-native GitHub Actions result with a concrete reference for the exact head; a local verifier result alone is not a landing gate. Required documentation must also be `pre_merge_complete` or an evidenced reviewed `none`. After confirmed merge evidence, invoke `project_management_documentation_reconcile` when documentation reconciliation is required. Work Management can then project `Documentation`/`Done`, but immutable Git/GitHub landing facts remain authoritative.

Review evidence writes only beneath `.work/reviews/<review-id>/`, uses atomic replacement, retains staged recovery evidence on failed replacement, and exposes no delete operation. `.github/workflows/work-management.yml` is now the canonical exact-head verification workflow: pull requests to `main` trigger it automatically, Actions are pinned by immutable SHA, the locked environment is synchronized once, and `scripts/verify.ps1 -SkipDependencySync` runs the single canonical repository verification pass, including governance validation. Do not add a second focused/full pass that repeats the same tests before or after it.

Current routing uses one shared user Project #1 backend with the stable `github-default` binding. `kis-mcp`, `chatgpt-skill`, `commodity`, and `college` are managed repositories; the Project coordinate is registered once through `kis-mcp` while each repository keeps its own central-registry identity. Live evidence from 2026-08-13 confirms the Project is reachable but still has only GitHub built-ins plus `Status = Todo / In Progress / Done`; the remaining rich-field/12-view provisioning gap is recorded in the commissioning guide. Change 113 also backfilled recent slice and residual records into the live Project through preview-first reconciliation. All custom/native automation remains disabled. Runtime-scoped GitHub OAuth remains a separate supervised connection state.

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

Request limits are optional and may only narrow values in `settings.discover.limits`. For a root registered in `settings/projects.settings.json`, `inspect_project` creates or reuses the project/worktree generation under the configured Discover state root; `get_code_context`, `inspect_change` impact analysis, and `analyze_change` consume the same normalized intelligence. Generation applicability includes stable `project_id`, canonical/worktree identity, Git/source fingerprint, Discover settings/index fingerprints, and semantic-provider fingerprint. A stale, incompatible, or corrupt generation is never represented as current: it is refreshed on demand, with superseded/corrupt state retained recoverably. The result contains versioned repository, evidence, local Git, verification-discovery, Python-structure, persistent symbol/relationship, confidence, freshness, truncation, and handoff records. Verification declarations are evidence only: Discover does not execute repository code, tests, builds, or discovered commands.

`inspect_change` is exposed through the same transports for bounded local working-tree, staged, commit, range, or branch evidence. Working-tree inspection is the default:

```json
{
  "path": "C:\\Projects\\example"
}
```

For an exact local commit, supply the bounded target explicitly:

```json
{
  "path": "C:\\Projects\\example",
  "source": "commit",
  "commit_ref": "HEAD"
}
```

Range and branch targets use `source` plus `base_ref` and `head_ref`; staged inspection uses `source: "staged"`. The public result preserves rename, copy, delete, type-change, and conflict path evidence where applicable and adds a deterministic change fingerprint, conventional file classifications, affected top-level scopes, impact counts, diagnostics, explicit unknowns, confidence, and truncation state. All target readers use fixed local Git templates and remain read-only. Pull-request and trusted remote evidence are not fetched by `inspect_change`; supplied GitHub change context is handled only by the bounded `analyze_change` contract.

`DISCOVER_*` errors are structural and corrective. They are not HR policy decisions. Resolve the reported path, unsafe link/reparse condition, unsupported or excessive request limit, unreadable text, Git metadata condition, or configured budget rather than changing `policy/kis-mcp.policy.json`.

## Inspect provider runtime status

Call `kis_provider_status` to inspect the current Provider catalogue and runtime composition. For each approved external provider, read these fields separately:

- `registered` and `enabled` — descriptor and runtime selection state;
- `build_attempted`, `built`, `mounted`, and `state` — this process's composition result;
- `readiness` — provider-neutral local preflight and current runtime evidence;
- `user_status` — the current user-facing state and exact next action;
- `commissioning` — separate installation, configuration, authentication, upstream connection, tool discovery, and live-verification states.

Interpret the normal onboarding states as follows:

- **DBHub: `Unavailable — DBHub pinned installation required`** means the KIS DBHub settings and registered bindings can be valid while the exact upstream artifact is absent. The checked-in College `results` SQLite binding is local/read-only and requires no credential; do not substitute `latest` or an unverified release. Current commissioned state uses exact `v1.2.0` / `1bed0b8bd8e6e3e625c83f571d12f748f2d7a0b0` and has live-verified the College binding.
- **Docker Hub: `Unavailable — Docker Hub pinned installation required`** means the exact approved Docker Hub source tree has not been activated beneath `C:\Projects\.kis-mcp\providers`. Checked-in mode is public, so no PAT is required and no project namespace binding is assumed. Current commissioned state uses exact `ad806e2cab0489a296aec0f32f3d3eea807d65c2` in public mode.
- **Docker Hub PAT mode** is optional. JSON stores only username plus a canonical `secret://...` reference; startup resolves the referenced value through the existing supervised vault boundary and forwards only `HUB_PAT_TOKEN` to the Docker Hub child.
- **GitHub: `Ready — authentication required`** means the pinned executable, OAuth mode, provider configuration, and runtime-scoped client path are ready but the shared provider lifespan has not yet proved the current OAuth identity. Start `kis-op` and complete one supervised OAuth sign-in for that runtime.
- **GitHub: `Ready — authenticated`** means the current running provider lifespan completed `get_me` and initial upstream tool discovery successfully. Subsequent GitHub operations and long-tail discovery reuse that same provider process until `kis-op` stops. This is runtime evidence, not persistent authentication across restarts and not a claim that every GitHub operation was live-verified.
- **Supabase: `Ready — authentication required`** means the unscoped account endpoint, Windows credential storage, and provider configuration are ready; complete one browser OAuth login for the running KIS runtime.
- **Supabase: `Ready — authenticated`** means the persistent account-scoped client is connected and upstream tools are discovered. Explicit registered-project live verification may still be pending and is reported separately.

A mounted provider is not automatically authenticated, upstream-connected, tool-discovered, or live verified. Reserve degraded, unavailable, or failed states for genuine local faults such as a missing executable, unavailable Windows credential storage, a legacy PAT conflict, invalid configuration, builder failure, mount failure, protocol failure, or runtime failure. `build_failed` with `RuntimeError` for GitHub indicates a local builder or settings failure, not a normal sign-in requirement. Do not add PATs, OAuth values, DSNs, project references, or other credential values to repository JSON.

### Activate and commission DBHub / Docker Hub

KIS does not fetch these providers during startup or commissioning. First provision an **exact local source checkout beneath `C:\Projects`** at the configured revision and build or stage the provider during a separately supervised bootstrap step. Existing provider state is moved to quarantine before replacement; nothing is permanently deleted.

Prefer a lean deployment subdirectory inside the exact checkout when dependency-manager links or workspace layout would make a recursive copy expand substantially. The deployment root must still resolve the approved parent Git revision with `git -C <deployment-root> rev-parse HEAD` and must contain `dist\index.js`. For DBHub `v1.2.0`, the official MCPB release bundle is a valid source of the runtime files after its bundled `server` directory is staged as `dist`; verify the entry-point bytes against the exact source build before activation.

```powershell
pwsh -NoProfile -File .\scripts\activate-db-docker-providers.ps1 `
  -DBHubSourceRoot C:\Projects\<exact-dbhub-checkout>\<deployment-subdir> `
  -DockerHubSourceRoot C:\Projects\<exact-dockerhub-checkout>\<deployment-subdir>
```

The script verifies `git rev-parse HEAD`, requires `dist\index.js`, copies only the supplied exact-revision tree into the JSON-governed provider location, and records SHA-256 installation identity. It refuses `latest`, an unpinned revision, a source outside `C:\Projects`, or a missing built entry point. Do not pass a workspace root whose pnpm/npm links cause recursive-copy expansion; stage a lean runtime subtree instead.

Then run:

```powershell
pwsh -NoProfile -File .\scripts\commission-db-docker-providers.ps1
```

The commissioning command reports installation, configuration, authentication, upstream connection, tool discovery, and live verification separately. DBHub generates one runtime TOML and starts one isolated child per registered binding. College currently exposes only `db_college_results_search_objects` and `db_college_results_execute_sql`; the latter is forced read-only with the JSON-owned row bound. Current live evidence includes a successful `SELECT 1 AS commissioned` against the College SQLite binding.

Docker Hub is commissioned in public mode with no project binding. The current KIS surface exposes `checkRepository`, `checkRepositoryTag`, `getRepositoryInfo`, `getRepositoryTag`, `listRepositoriesByNamespace`, and `listRepositoryTags`. Do not expose upstream `search` with the current pinned revision: as verified on 2026-08-13, Docker Hub returns a top-level `search_after` field that violates that provider revision's declared closed output schema, causing MCP result validation to fail after a successful upstream response. Re-enable it only after an approved provider update or compatibility fix is separately verified. Switching to PAT mode requires an explicit username and canonical vault reference, not a checked-in token. Recovery uses the quarantined prior provider tree plus a KIS restart.

For bounded Context7/Serena commissioning, run from the source checkout through the locked environment:

```powershell
$env:UV_PROJECT_ENVIRONMENT='C:\Projects\.kis-mcp\python-env'
$env:UV_CACHE_DIR='C:\Projects\.kis-mcp\uv-cache'
uv run --offline --no-sync python scripts\run-provider-live-smoke.py
```

The smoke validates local Context7 MCP startup/tool discovery without bypassing HR-002, starts Serena with `UV_OFFLINE=1`, reconciles its central per-project state location before activation, performs bounded semantic reads, and proves Serena HR3-07 memory safety by quarantining the exact pinned 1.6.1 memory artifact, restoring it, restarting Serena, and rechecking the derived memory catalogue/content. Test source projects live beneath `C:\Projects\.kis-mcp\commissioning`; their Serena-generated state lives separately beneath `C:\Projects\.kis-mcp\serena\projects`. The smoke never creates project-local `.serena`, never treats Serena memory as KIS project memory, and never forwards permanent deletion after successful quarantine.

## Authenticate GitHub MCP

GitHub OAuth is owned by the running `kis-op` process. Ensure `GITHUB_PERSONAL_ACCESS_TOKEN` is unset; a PAT override is a configuration conflict and is never forwarded to the official GitHub MCP subprocess.

Start the operation runtime through the GitHub auth helper:

```powershell
pwsh -NoProfile -File .\scripts\auth-github-mcp.ps1
```

The helper validates the GitHub provider settings and central project registry, then starts `kis-op`. The provider-lifetime `get_me` call triggers the official browser OAuth flow once after the shared client connects. The launcher gives this supervised server/authentication phase its own 900-second default budget; `-AuthenticationTimeoutSeconds` may be set from 30 through 3600 seconds when needed. GitHub MCP stderr is drained continuously into the retained per-run server stderr log and echoed in the visible launcher, so browser/device-code fallback guidance remains visible while sign-in is pending. After the local MCP runtime becomes ready, the normal `-TimeoutSeconds` budget starts fresh for tunnel startup and readiness. Complete the sign-in and keep the `kis-op` runtime running; subsequent GitHub tool calls during the same runtime reuse the authenticated subprocess. Stopping or restarting `kis-op` discards the official provider's process-memory token and requires one new sign-in.

Run the focused non-live verification independently:

```powershell
pwsh -NoProfile -File .\scripts\smoke-github-mcp.ps1
```

This verifies the runtime client lifecycle, central project-registry wiring, GitHub registered-coordinate routing, scripts, and legacy repository-settings compatibility without claiming live authentication. Use `-RequireLive` only for an explicit supervised live commissioning check; it may require interactive OAuth and remains separate from repository verification.

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

NVIDIA NIM remains one backend with three named model profiles. `super` is the default when no model is specified:

| Profile | Model | Use it for |
|---|---|---|
| `nano` | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` | Fast first-pass review, focused diffs, routine regression/error-handling checks, triage, and repeated iterative review where responsiveness matters. |
| `super` | `nvidia/nemotron-3-super-120b-a12b` | Default substantive review: multi-file changes, correctness and regressions, implementation-plan checks, and broad repository-context analysis. |
| `ultra` | `nvidia/nemotron-3-ultra-550b-a55b` | Deepest/high-impact analysis: architecture, subtle cross-component failures, complex state/concurrency, difficult failure analysis, and safety/security-sensitive review. |

The configured NVIDIA parameters are profile-specific. KIS uses non-streaming chat completions for this advisory workflow. Nano's upstream model supports multimodal inputs, but `review_change_with_agent` currently supplies text repository evidence only; this workflow does not claim image, audio, or video review.

The NVIDIA API key is stored in the application-managed encrypted vault under the canonical non-secret reference:

```text
secret://provider/nvidia-nim/api-key
```

`settings/agents/code-review-agent.settings.json` stores only that reference and the process environment name `NVIDIA_API_KEY`, never the credential value. To set or replace the credential through the supervised vault path:

```powershell
pwsh -NoProfile -File .\scripts\set-secret.ps1 -Reference secret://provider/nvidia-nim/api-key
```

The script prompts for the vault unlock material and secret value using secure input. Do not use a repository `.env` file as a persistent credential store; `.env/` is ignored. Vault content changes remain interactive. Ordinary KIS startup is non-interactive: `scripts\start-chatgpt.ps1` reads the cryptographically verified runtime vault unlock from Windows Credential Manager, resolves the configured NVIDIA vault reference only while starting the selected server child, injects it as process-scoped `NVIDIA_API_KEY`, then clears transient launcher references. Starting `kis-dev` does not inspect, stop, or reconfigure the peer `kis-op` instance.

For an existing vault, configure the runtime credential once from a local supervised terminal:

```powershell
pwsh -NoProfile -File .\scripts\configure-secret-runtime-unlock.ps1
```

That command asks for the existing vault unlock, verifies it against the encrypted vault, and only then stores it under the current Windows user. Vault initialization creates the runtime credential after successful initialization; master-key rotation updates it only after successful rotation. `set-secret.ps1` still asks for the vault unlock and never rewrites the runtime credential. Do not put the NVIDIA key or vault unlock in repository JSON, command arguments, logs, MCP requests, or retained startup state.

Model selection is explicit and bounded. Example:

```json
{
  "path": "C:\\Projects\\example",
  "instructions": "Prioritize correctness, error handling, and regressions.",
  "backend": "nvidia-nim",
  "model": "super"
}
```

`model` accepts only `nano`, `super`, or `ultra`. Omitting both `backend` and `model` uses the configured preferred/fallback order and defaults NVIDIA to `super`. Supplying a model without `backend` explicitly selects NVIDIA and does not silently fall back to Codex. Supplying an NVIDIA model together with `backend="codex-cli"` is an invalid request rather than an ignored setting.

Codex CLI is a pinned, project-contained independent reviewer. KIS installs exact `@openai/codex@0.147.0` beneath `C:\Projects\.kis-mcp\tools\codex\0.147.0` and keeps its authentication/state profile beneath `C:\Projects\.kis-mcp\agent-hosts\codex-reviewer`. Installation is an explicit supervised bootstrap operation:

```powershell
pwsh -NoProfile -File .\scripts\install-codex.ps1
```

Authenticate that managed profile with the operator's ChatGPT subscription rather than an OpenAI API key:

```powershell
pwsh -NoProfile -File .\scripts\auth-codex.ps1
```

The auth script runs Codex's ChatGPT login flow under the managed `CODEX_HOME`, removes API-key override variables for that process, and verifies `codex login status` reports ChatGPT authentication. KIS readiness also requires the exact configured CLI version and ChatGPT-authenticated managed profile.

`review_change_with_agent` accepts exactly one `review_type`: `code-quality` (default), `safety-security`, `architecture`, `performance`, `test-quality`, `documentation`, or `api-contracts`. The specialist purposes apply focused rubrics to the same bounded repository evidence and backend contract: architecture covers boundaries/coupling/contracts; performance covers likely cost and measurement gaps without inventing benchmarks; test-quality covers coverage and failure-path quality; documentation covers current claims and authority consistency; API/contracts covers schemas, compatibility, errors, and versioned interfaces. Every purpose requires evidence-backed findings and retains the same no-mutation/no-nested-agent boundary.

To force an independent Codex review with no NVIDIA fallback:

```json
{
  "path": "C:\\Projects\\example",
  "backend": "codex-cli",
  "review_type": "safety-security",
  "instructions": "Review the current change only; prioritize concrete exploitable or policy-relevant findings."
}
```

Explicit `backend="codex-cli"` invokes only Codex. Omitting `backend` retains the configured NVIDIA-first fallback order. NVIDIA `model` aliases are invalid with Codex.

The gateway invokes only `scripts\invoke-codex-agent.ps1`, passes the prompt through standard input, sets the managed `CODEX_HOME`, removes API-key override variables for the Codex process, and requests:

```text
codex exec --ephemeral --json --sandbox read-only --color never -C <project> -
```

The read-only sandbox is defense in depth. The wrapper fingerprints Git-visible repository state before and after the run, including HEAD, status, tracked diff, and untracked-file content hashes. Any change fails with `CODEX_CLI_MUTATION_DETECTED`; KIS never silently accepts or overwrites it.

Tests cover NVIDIA profiles, explicit review purposes, Codex exact-version/auth readiness, read-only wrapper mutation detection, fallback semantics, secret redaction, non-interactive vault-backed startup, and additive tool registration. Live upstream commissioning remains distinct from deterministic repository verification.

## Run the KIS Control Center

The KIS Control Center is a read-only MCP App available both through the mounted `controlcenter_*` provider and as a standalone process. Neither form authorizes Work mutations or changes the HR-001 / HR-002 / HR-003 enforcement boundary.

Run it from the source checkout through the locked project interpreter:

```powershell
C:\Projects\.kis-mcp\python-env\Scripts\python.exe -m kis_mcp.control_center
```

The server reads `settings\control-center.settings.json` and exposes:

- `open_kis_control_center` — a bounded structured local snapshot;
- `ui://kis-mcp/control-center.html` — a self-contained local MCP App resource.

The snapshot reports runtime identity, configured project and local Git state, the exact three-rule declaration, provider configuration with runtime-check requirements, bounded quarantine counts, verification guidance, and structural diagnostics. It performs no mutation or network access. Provider configuration does not prove provider authentication or commissioning, and verification remains unrecorded until current evidence is run. When the standalone app has no owning gateway provider-status source, runtime mount state is reported as unavailable rather than inferred as zero mounted providers.

## Diagnose long-lived ChatGPT tool binding

KIS remote HTTP is stateless; do not add conversation leases or per-repository KIS runtimes to diagnose an old chat that loses tool use. `kis_health` exposes the current runtime identity, process-stable `server_instance_id` and `server_started_at`, source revision, public-contract fingerprint, and transport flags. Control Center **Recent Calls** retains bounded correlation records for `initialize`, `tools/list`, and `tools/call` plus existing tool names, argument key names, decisions, and outcomes. It does not retain prompts, argument values, result bodies, or credentials.

When an old chat appears unable to use `kis-op` or `kis-dev`:

1. Do not restart KIS first.
2. Call `kis_health` from the old chat if possible and record only the returned fingerprint fields.
3. Open a new chat against the same app/runtime and call the same `kis_health`.
4. Open Control Center and compare recent MCP-boundary request IDs/timestamps for the two attempts.
5. If the old attempt produced no inbound boundary record while the new attempt did, treat the evidence as a ChatGPT/app-binding failure outside the KIS request path. If both attempts reached KIS, diagnose the recorded outcome and exact server/contract fingerprint before restarting anything.

This diagnostic distinguishes request arrival from KIS processing without changing the three-rule Work policy or logging conversation content.

## Commission Supabase OAuth

Use only a development or test Supabase project. The account-scoped provider exposes read/write capabilities, while KIS project routing is enforced separately from `settings/projects.settings.json`.

Ensure the intended project is registered and clear the legacy PAT variable. `SUPABASE_PROJECT_REF` is not required:

```powershell
Remove-Item Env:SUPABASE_ACCESS_TOKEN -ErrorAction SilentlyContinue
```

Run the non-network OAuth preflight:

```powershell
pwsh -File .\scripts\smoke-supabase-mcp.ps1
```

Preflight validates schema version 3, the unscoped official endpoint, Windows Credential Manager availability, and absence of the legacy PAT conflict. It does not contact Supabase or prove authentication.

Start explicit browser OAuth commissioning:

```powershell
pwsh -File .\scripts\auth-supabase-mcp.ps1
```

FastMCP performs OAuth discovery and dynamic client registration against `https://mcp.supabase.com/mcp`. Client and token state are persisted under the `kis-mcp/supabase` Windows Credential Manager service. The commissioning client resolves the default registered KIS project, lists the upstream surface, and invokes only `get_project_url` with that explicit registered `project_id`. It verifies that the returned hostname matches the registry binding without printing the project URL or project reference.

After authorization succeeds, prove runtime-client reuse and namespaced shared-runtime exposure:

```powershell
pwsh -File .\scripts\smoke-supabase-mcp.ps1 -SharedRuntime
```

The shared smoke requires Supabase to be mounted in `kis_provider_status` and invokes only `supabase_get_project_url` with the explicit registered project ID. Read-only account discovery such as `supabase_list_projects` may remain available. Mutating tools may be discoverable but are not invoked by commissioning; targetless mutations are rejected.

Use `-Live` for a standalone authenticated recheck:

```powershell
pwsh -File .\scripts\smoke-supabase-mcp.ps1 -Live
```

Never set `SUPABASE_ACCESS_TOKEN`; PAT transport is intentionally unsupported. Project references are non-secret routing coordinates and belong only in the central registry; never commit access tokens, refresh tokens, client secrets, authorization codes, keyring values, or returned project URLs.

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
- reclaims a selected-instance listener or orphan process tree only when the canonical project Python launch path, exact remote-runtime instance, profile, and endpoint identity match; Windows may report the underlying base Python as `ExecutablePath`, so the canonical launch path may instead be proven by the first command-line token; an unrelated listener fails with PID/process diagnostics and is never terminated;
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

Create the local governed change first. Work Management linkage is optional projection metadata and may be added at creation or reconciled later. Choose the executable risk profile explicitly when it differs from standard:

```powershell
pwsh -File .\scripts\change-workflow.ps1 new 002-example-change `
    --outcome "Implement one bounded result" `
    --risk-profile lean `
    --owned "src/example/**" `
    --owned "tests/test_example.py" `
    --exclude "policy/**"
```

Schema-version-3 `new` records the local base commit/tree and classifies supplied or locally available remote-tracking evidence as `same_sha`, `tree_equivalent`, `content_divergence`, or `unavailable` without contacting the provider. `lean` creates `scope.json` plus `change.md`; `standard` and `rigorous` create the full five-file lifecycle record. Historical schema-version-1/2 scopes remain valid under their original compatibility rules. Generated tracked artifacts use explicit LF bytes on every host so Windows newline translation cannot create a `core.safecrlf` staging failure.

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

Cleanup refuses a dirty worktree or an unmerged branch. It performs only normal `git worktree remove`, `git branch -d`, and `git worktree prune` operations; it never forces deletion. For schema-version-3 changes, successful merged cleanup establishes historical closed state without a second repository commit solely to rewrite lifecycle metadata.

## Verify

During development, run focused and affected checks. The normal pull request to `main` owns the single canonical full verification pass on the exact GitHub head. For an explicit local canonical run outside that PR path:

```powershell
pwsh -File .\scripts\verify.ps1
```

Verification requires `uv.lock`, synchronizes the external Python environment offline with `--frozen`, and invokes `scripts\verify.py` through that environment's exact Python executable. In GitHub Actions, the workflow synchronizes the locked environment once and invokes `scripts\verify.ps1 -SkipDependencySync` so dependency preparation is not repeated. The Python verifier confirms the interpreter location, FastMCP 3.4.4, pytest `>=8.4,<9`, Python syntax, configuration, and the full test suite.

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
