# kis-mcp Product Specification

## Goal

Provide a private, operator-supervised FastMCP gateway that exposes Desktop Commander's normal local development tools while enforcing exactly three prohibited intents:

1. writing outside `C:\Projects`;
2. external network operations through the local Work path;
3. permanent deletion instead of recoverable quarantine.

Everything else remains available through ordinary tooling.

## Greenfield boundary

The repository contains only:

- integration with the authoritative Desktop Commander distribution;
- a small FastMCP forwarding and enforcement layer written for this project;
- recoverable quarantine support;
- minimal JSON configuration, tests, and operational documentation.

The repository does not contain an inherited SDK2 runtime, a custom replacement filesystem or terminal, a capability-profile permission framework, a governance subsystem, or a fork of Desktop Commander. It implements bounded Discover, Skills, Provider, Tools, workflow, and Control Center modules natively under `src/kis_mcp`; donor repositories remain source evidence only and are not runtime dependencies. Reusable procedures are accessed only through the KIS Skills module. The module resolves the operator-approved shared catalogue through `settings/skills.settings.json`; the repository does not carry a local skill catalogue, and Skills mutations re-enter the existing Work middleware and Desktop Commander backend.

## Product evolution

This specification defines the current implementation baseline. [`docs/PLATFORM-CONCEPT.md`](docs/PLATFORM-CONCEPT.md) defines the approved target architecture.

The platform uses three capability planes:

```text
Discover → establish bounded repository evidence
Govern   → evaluate evidence against declared standards
Work     → perform controlled change under HR-001 / HR-002 / HR-003
```

The current gateway implements Work, bounded Discover with persistent registered-project intelligence, Skills, Provider and Tool composition, a normalized capability catalogue, readiness-aware progressive exposure, first-class workflow descriptors and recommendations, effect-specific long-tail dispatch, quarantine operations, and one executable advisory code-review workflow. Discover persists bounded derived Code Atlas, Symbol Atlas, and Relationship Graph generations beneath the central KIS state root and may enrich them with optional normalized Serena semantics; repository/Git/document evidence remains authoritative. Govern remains target-state work.

### Capability exposure

| Exposure | Current capability |
|---|---|
| Direct gateway profile | A JSON-bounded set of frequent Desktop Commander, gateway, Discover, advisory-review, capability-discovery, effect-specific dispatch, and Control Center entry points. Only eligible ready or degraded operations enter the normal direct surface. |
| Discoverable long tail | Remaining registered Desktop Commander, Skills, internal Discover, quarantine, and namespaced provider operations. They retain original schemas and middleware, are searchable by capability, and may be invoked through effect-specific dispatch when eligible. |
| Status-only | Disabled, unavailable, authentication-gated, build-failed, or mount-failed operations remain visible through provider and capability status but are not normally exposed or recommended. |
| Standalone | KIS Control Center read-only MCP App and UI resource. It remains available as an explicit operator-launched surface, while the default gateway provider composition keeps it disabled. |
| Managed support tooling | AgentSys `6.0.1` host profiles and agnix `0.45.0` are installed through supervised bootstrap scripts beneath `C:\Projects`. Agnix uses the operator-approved ignored repo-local runtime path `C:\Projects\kis-mcp\.temp\tools\agnix\0.45.0` for Windows application-control compatibility and is exposed only through bounded `validate_agent_configuration`; neither tool is mounted as a general provider. |
| Target | Govern operations, broader semantic and trusted remote evidence, and additional executable workflow orchestration. |

The future platform model does not alter the closed Work enforcement decision set. Profiles, catalogues, governance findings, evidence requirements, readiness, or workflow selection must not become additional reasons to block an otherwise permitted invocation.

## Components

| Component | Responsibility |
|---|---|
| Desktop Commander | Provides ordinary filesystem, edit, search, process, testing, and local-development tools. |
| FastMCP gateway | Composes domain platform entry points, owns instance-scoped capability and readiness state, presents the curated tool surface, evaluates concrete Work invocations, and forwards allowed calls through original contracts. |
| Discover module | Exposes bounded `inspect_project`, `inspect_change`, `get_code_context`, and `analyze_change`; all share one registered-project intelligence service that persists bounded Code Atlas, Symbol Atlas, and Relationship Graph generations with freshness/fingerprint/provenance metadata and deterministic local fallback. |
| Skills module | Resolves the approved shared catalogue, overlays reviewed category and capability metadata, contributes Skills to the normalized catalogue, routes create/improve mutations back through Work middleware, and records bounded redacted usage/outcome telemetry for downstream evaluation. |
| Provider runtime | Registers Desktop Commander, Context7 MCP, DBHub, Docker Hub MCP, GitHub MCP, NVIDIA NIM, Serena MCP, Supabase, and Control Center descriptors; mounts enabled connectors under unique namespaces; keeps Context7 independent from project memory; exposes Serena only through a read-only semantic surface with offline-enforced startup; creates one isolated DBHub proxy per registered database binding; keeps Docker Hub separate from local Docker Engine operations; owns runtime-scoped provider clients; contains failures; and reports readiness and commissioning separately. |
| Capability composition | Normalizes Provider, Tool, Discover, Skill, and Workflow contributions; evaluates readiness and eligibility; scores explainable recommendations; and plans direct, discoverable, or status-only exposure. |
| Tools and workflows | Registers local executable adapters such as Codex CLI, contributes normalized operations, describes complete user workflows, exposes bounded advisory code review with NVIDIA/Codex backend selection, and exposes pinned agnix validation through fixed read-only arguments with no fix authority. |
| Execution substrate | Defines provider-neutral execution request/result/readiness/lifecycle contracts. Verification continues to use `local-process` by default. Disabled-by-default `windows-virtualbox-proof` and `windows-hyperv-proof` profiles provide internal exact-source disposable Windows proof paths with bounded provenance/evidence and fail-closed lifecycle outcomes; the shared proof adapter is backend-neutral. VirtualBox is the first commissioning path, Hyper-V remains an alternate provider, and profile availability does not imply live host commissioning. |
| Managed bootstrap tooling | Installs pinned Codex CLI, AgentSys, and agnix distributions beneath `C:\Projects`; activates only locally provisioned exact-revision DBHub/Docker Hub artifacts beneath `C:\Projects\.kis-mcp\providers`; creates isolated managed profiles; validates staged state; and preserves replaced state through quarantine without expanding Work authority. |
| Control Center | Provides a read-only MCP App and UI resource. The checked-in gateway composition disables the `controlcenter_*` provider by default; an operator may explicitly enable that existing provider entry and restart the selected runtime, or launch the standalone process. It does not authorize Work mutations. |
| Effect resolver | Extracts explicit content-write paths, directory-entry mutations, network intent, and delete intent from provider arguments and command text. |
| Three-rule policy | Returns only allow, block HR-001, block HR-002, quarantine HR-003, or block HR-003. |
| Quarantine service | Moves delete targets intact beneath `C:\Projects\.kis-mcp\quarantine\<operation-id>`. |
| Verification suite | Tests configuration, path boundaries, provider mappings, command-intent detection, and quarantine behavior. |

## Request flow

```text
ChatGPT
   |
   v
kis-mcp FastMCP gateway
   |
   +--> preserve Desktop Commander tool contract
   +--> resolve the concrete invocation intent
   +--> apply only HR-001 / HR-002 / HR-003
   |       |
   |       +--> no prohibited intent: forward
   |       +--> HR-001 or HR-002: reject with corrective detail
   |       +--> HR-003: quarantine or reject if quarantine is unsafe
   |
   v
Desktop Commander
   |
   v
local development environment
```

## ChatGPT remote transport

The ChatGPT-facing private path uses the same `build_server()` gateway and tool catalogue as local stdio:

```text
ChatGPT developer-mode app
        |
        v
OpenAI-hosted Secure MCP Tunnel endpoint
        |
        v
operator-supervised tunnel-client
        |
        v
127.0.0.1:<instance-port>/mcp
        |
        v
kis-mcp FastMCP gateway -> Desktop Commander
```

`settings.remote_mcp` defines exactly two local instances: internal `operation`, exposed in ChatGPT as `kis-op` on `127.0.0.1:8010`, and internal `development`, exposed as `kis-dev` on `127.0.0.1:8011`. Each record has a distinct app name, port, profile name, tunnel ID, vault secret reference, runtime directory, and explicit `configured` state. Selection is explicit through the launcher instance argument or the JSON `active_instance`; both instances may run concurrently, and the runtime does not perform automatic failover.

Both instances compose the same backend capabilities and use the same JSON-defined direct profile. Progressive exposure reduces default tool-schema context but does not remove eligible backend operations: long-tail operations remain discoverable and execute through their original schemas and middleware. Transport, instance name, profile, catalogue metadata, approval metadata, recommendation score, or risk labels do not create enforcement decisions. Only provider functionality whose every invocation is necessarily external-network-only may be omitted; the current pinned exceptions remain the feedback tool and `read_file.isUrl` mode.

The tunnel is an operator-supervised connector boundary outside ordinary Work invocations. It does not change the closed HR-001 / HR-002 / HR-003 decision set. Tunnel credentials are stored in the application-managed encrypted vault under the non-secret `tunnel_secret_ref` values recorded in checked-in JSON. Setup and startup unlock the vault through the supervised secret-process boundary, resolve only the selected reference, pass the value through process-scoped environment state, and do not persist it in repository files, generated profiles, or runtime state. Generated profiles and runtime diagnostics remain beneath `C:\Projects\.kis-mcp\tunnel-client`.

## Desktop Commander integration

Use `@wonderwhy-er/desktop-commander` from its authoritative source. Pin the tested package version in `settings/kis-mcp.settings.json`.

Install the provider beneath `C:\Projects\.kis-mcp\desktop-commander`; do not vendor or fork it in this repository. Keep npm cache, provider configuration, logs, and generated state beneath `C:\Projects\.kis-mcp`.

Preserve provider tool names, descriptions, and schemas unless a minimal FastMCP compatibility transform is required. Do not recreate provider functions.

Network-only provider tools are omitted from the Work surface when the pinned provider contract proves every invocation is external-network-only. Network-only modes inside an otherwise local tool are removed from the exposed schema. These are contract-shaping controls, not additional policy mappings, and calls that manually supply the removed surface fail as structural unsupported-provider errors.

Desktop Commander's provider-native `blockedCommands` and `allowedDirectories` fields must remain empty. Startup verifies those invariants, and the exposed provider configuration tool cannot modify them. This prevents the provider from silently adding a command denylist or directory allowlist beneath the FastMCP boundary; it does not create another Work rule.

## Policy input

The policy core receives provider-neutral facts for one invocation:

- paths explicitly targeted for content creation, modification, or generated output;
- paths whose directory entries are explicitly moved or renamed;
- paths explicitly targeted for deletion;
- whether the invocation explicitly requests external network access.

The policy core does not inspect tool names or command strings. Provider-specific parsing belongs in the adapter.

## Enforcement proof standard

The enforcement point is the actual concrete invocation and its resolved resultant effects, not the natural-language prompt in isolation and not an individual tool, command, executable, URL, flag, or capability category.

The resolver must evaluate the relevant combination of tool contract, arguments, modes, working directory, explicit targets, composed command segments, and other concrete facts. A hard-rule decision is permitted only when that combined evidence proves the invocation will produce HR-001, HR-002, or HR-003.

If the prohibited effect cannot be positively established, the invocation remains allowed. Possibility, likelihood, unfamiliarity, parser limitations, incomplete static prediction, or destructive appearance do not satisfy the proof standard.

Malformed or structurally invalid input may produce a separate corrective input error. It must not be reported as a hard-rule violation without proof of the prohibited effect.

An inherently external-network-only provider capability may be omitted from the Work surface when every supported invocation necessarily violates HR-002. Once omitted, the gateway should not maintain redundant URL or argument restrictions for that unavailable capability. Mixed-purpose and general command tools remain exposed and are evaluated only at concrete invocation level.

## Closed decision set

```text
allow
block: HR-001
block: HR-002
quarantine: HR-003
block: HR-003
```

No readiness, capability, approval, allowlist, denylist, or uncertainty state may block an otherwise permitted invocation.

## HR-001 — Write boundary

Normalize paths before comparison. Resolve existing links and junctions in the effective write path. A path is inside the boundary only when it equals `C:\Projects` or is a true descendant. Prefix similarity such as `C:\Projects-old` is outside.

Content writes follow the final target. Directory-entry mutations such as move, rename, and quarantine resolve existing ancestors but act on the final entry itself. A move changes both source and destination; block when either explicit entry is outside the boundary.

Relative paths are resolved against the concrete working directory supplied by the provider invocation. When no working directory is supplied, use the configured project boundary.

## HR-002 — External network

Block only a concrete Work invocation whose resolved operation consumes an external target. Current exact evidence includes:

- a known network client with an external target in a consuming argument position;
- an explicit external package URL, remote Git dependency, registry endpoint, or package source option;
- a Git remote operation whose explicit target or locally resolved remote configuration is external;
- enabling Desktop Commander telemetry with a value that the pinned provider does not interpret as disabled.

The following do not independently establish HR-002:

- a URL string in output, source text, search input, documentation, or an unrelated argument;
- a package-manager executable, operation name, package name, lockfile operation, or missing package operand;
- an unresolved Git remote alias;
- a program that is merely capable of opening a socket;
- an unknown command or unsupported parser case.

Provider-only external-network capabilities are removed from the exposed Work contract rather than redundantly classified by the policy resolver. In the pinned provider this includes the feedback tool and the `read_file.isUrl` mode. A manually constructed call using an unexposed tool or argument receives a structural unsupported-surface error, not an HR decision.

Automatic provider activity that occurs before ordinary invocation enforcement is handled separately as startup containment, and only where the pinned provider source proves the external effect. The current verified cases are telemetry, the default external feature-flag endpoint, and automatic Chrome download when no local installation or cache exists.

Operator bootstrap and approved ChatGPT connectors are separate supervised paths outside local Work.

## HR-003 — Permanent deletion

Never forward explicit delete intent as permanent deletion.

For an eligible target inside `C:\Projects`, create a unique quarantine operation directory, move the target intact, and write bounded restoration metadata. If the move cannot be completed safely, reject the invocation.

Terminal commands that explicitly request deletion are transformed or rejected under HR-003. Restoration must not overwrite an existing original path.

## Terminal and process tools

Terminal and process tools remain available by default.

The adapter examines the concrete executable, arguments, command text, working directory, and explicit redirections for evidence of HR-001, HR-002, or HR-003. When no prohibited intent is resolved, the invocation is forwarded.

Tool breadth, arbitrary arguments, incomplete prediction of all possible side effects, or lack of a specialized parser are not independent reasons to block. Direct operator supervision is part of the trust model.

## Configuration

All project settings and policy declarations are JSON.

- `settings/kis-mcp.settings.json` defines identity, paths, provider source/version/launch configuration, Discover retrieval settings, the local stdio transport, and the ChatGPT remote transport.
- `settings/execution-runners.settings.json` defines execution backend/profile selection and provenance requirements. `local-process` remains the default verification backend. `windows-virtualbox-proof` and `windows-hyperv-proof` are disabled by default and require explicit readiness plus exact source/image/profile/toolchain identity before disposable guest execution. The VirtualBox profile additionally confines `VBOX_USER_HOME`, VM clone state, evidence, and guest password-file input to its KIS-owned state root.
- `settings.discover` defines the enable flag, exclusions, text types, encodings, hard-link behavior, file/directory/Git/index/output budgets, and the strict persistent-intelligence block: central state root, schema version, stored-byte/file/module/symbol/relationship limits, fingerprint fields, provider inclusion, corruption handling, and recoverable supersession behavior.
- `settings/providers/platform-runtime.provider.json` selects exactly the seven approved mounted MCP provider IDs, records runtime enablement, and assigns unique lower-case namespaces. It contains no credentials.
- `settings/providers/context7.provider.json` pins the independent Context7 external-documentation MCP installation and launch contract; it is not a Discover project-memory source.
- `settings/providers/dbhub.provider.json` pins the DBHub source/release identity, stdio entry point, generated-state root, row bound, and the read-only `search_objects` / `execute_sql` tool set. KIS generates one runtime TOML and one isolated DBHub child proxy per registered database binding; external DSNs are resolved only into process-scoped environment state.
- `settings/providers/dockerhub.provider.json` pins the official Docker Hub MCP source revision, stdio entry point, and public-or-PAT authentication metadata. Public mode stores no credential reference; PAT mode stores only a canonical vault reference and username, and the child receives only `HUB_PAT_TOKEN`.
- `settings/providers/serena.provider.json` pins Serena `1.6.1`, the relocatable venv-interpreter launch contract, contained provider state roots, and semantic-provider identity. Runtime startup enforces `UV_OFFLINE=1` and rewrites Serena's own global `project_serena_folder_location` to the JSON-governed central template `C:\\Projects\\.kis-mcp\\serena\\projects\\$projectFolderName\\.serena` before activation. KIS pre-creates that central path and binds each folder name to one normalized project root with a JSON identity marker, failing on collisions rather than sharing state. Repo-local `.serena` generation is not permitted; Serena memory files remain provider-managed state, not KIS project memory.
- `settings/providers/github-mcp.provider.json` contains only GitHub provider identity, pinned executable/source, OAuth mode, PAT-conflict metadata, and toolsets. Repository and GitHub Project routing are not provider-authentication settings.
- `settings/projects.settings.json` is the strict central project registry. It maps stable project IDs to absolute local roots and optional GitHub repository, GitHub Project, Supabase, database, and Docker Hub routing coordinates without storing credential values. Local database bindings use relative SQLite paths with no secret; external database bindings use only canonical `secret://...` references; Docker Hub project bindings store only non-secret namespaces.
- `settings/work-management/github-projects.settings.json` owns Work Management feature, gate, automation, evidence, and backend-binding behavior; `settings/work-management/github-project-schema.json` owns the desired **25-field / 12-view** GitHub Project operational projection, including each managed view's executable layout, filter, visible-field, sort/group, and board vertical-group semantics used for deterministic drift evidence.
- `settings.github_cli.config_dir` is the non-secret GitHub CLI authentication-state directory used only by KIS exact registered-repository mutations. It must resolve beneath `C:\\Projects`, remain outside the repository, and is passed to `gh`/Git only as process-scoped `GH_CONFIG_DIR`; KIS never reads or stores the credential value.
- `settings/kis-repository.settings.json` remains a legacy compatibility source for callers that explicitly use the repository-settings loader; gateway composition uses the central registry-backed selector instead.
- `settings/agents/code-review-agent.settings.json` defines the single advisory code-review agent, its NVIDIA NIM and Codex CLI backends, preferred/fallback order, evidence/output budgets, the canonical NVIDIA vault reference, exactly three NVIDIA profiles (`nano`, `super`, `ultra`) with `super` as default, and the pinned Codex executable/home/version. It stores no NVIDIA or Codex credential value. `settings/bootstrap/codex.install.json` separately pins exact `@openai/codex@0.147.0`, ChatGPT authentication mode, and all managed install/cache/home/quarantine paths beneath `C:\Projects`.
- `settings/secrets.settings.json` defines the encrypted application-vault metadata plus the non-secret Windows Credential Manager target used for the verified runtime unlock. Ordinary startup reads that current-user credential non-interactively; vault initialization, secret mutation, master-key rotation, and one-time existing-vault migration remain supervised operations.
- `settings.remote_mcp` defines the loopback HTTP endpoint, `C:\Tools\openai-tunnel-client\tunnel-client.exe`, the active instance, and separate `operation` and `development` records.
- Each remote instance stores its app name, port, profile name, explicit `configured` state, non-secret `tunnel_id`, and non-secret `tunnel_secret_ref` used to resolve its credential from the application-managed encrypted vault.
- `policy/kis-mcp.policy.json` contains exactly HR-001, HR-002, and HR-003.

A remote instance may have a blank tunnel ID only while `configured` is `false`. Before profile setup or startup, the operator supplies the real tunnel ID, changes `configured` to `true`, and stores the secret once with `scripts\set-tunnel-credential.ps1`. Profile setup and startup fail closed when the instance is unconfigured, its canonical vault reference is invalid, or the referenced vault entry cannot be resolved after supervised unlock. API keys, credential values, tunnel profile YAML, and generated runtime state are never committed.

Configuration and implementation-status fields do not disable otherwise permitted Desktop Commander tools or create another policy decision.

## Skills module

The implemented Skills module is the only agent-facing access path to the reusable procedure catalogue configured by `settings/skills.settings.json`. It builds a deterministic immutable snapshot after validating `SKILL.md` frontmatter, file paths, configured suffixes, encodings, links, sizes, and limits. The repository contains no local skill catalogue.

The module exposes bounded list, search, load, file-search, file-read, refresh, structural-evaluation, create, improve, attributed-outcome recording, and telemetry-report operations. Runtime cards are enriched from `settings/capabilities.settings.json` so every current shared Skill has a non-empty category, capability set, activation terms, effects, and workflow roles. ChatGPT loads the returned instructions and executes their workflows through ordinary kis-mcp Work tools; the server does not import or automatically execute arbitrary skill code.

Skill creation validates a complete proposed entrypoint, stages it beneath `C:\Projects\.kis-mcp\temp\skills`, and publishes it with Desktop Commander `create_directory`, `write_file`, and `move_file`. Skill improvement requires the active file SHA-256 and uses Desktop Commander `edit_block` with one exact expected replacement. Every mutation calls `FastMCP.call_tool(..., run_middleware=True)`, so the existing three-rule middleware evaluates the concrete Work effects.

Production composition also records bounded payload-free Skills evidence through the existing `RuntimeObservability` path and a KIS-owned SQLite store beneath the generated state root. Observed discovery/load/resource/evaluation/mutation events remain distinct from caller-reported `applied`/`completed`/`failed` outcomes, which require matching prior load attribution by skill/package identity and correlation fields. Reports keep usage/outcome counters and optional metric sample counts separate; they do not infer application from load or decide skill admission.

`settings/skills.settings.json` and `contracts/skills/settings.schema.json` define the exact roots, limits, supported suffixes, and traversal controls. Initial catalogue failure does not prevent ordinary Work/gateway startup; Skills calls return a corrective `SKILLS_*` error until the source is repaired and the server is restarted. `SKILLS_*` failures are structural or application errors and do not expand the closed Work policy decision set.

## Public interface

The public MCP presentation has three layers:

1. **Direct profile.** `settings/capabilities.settings.json` names a bounded frequent-use surface. It includes health and provider status, primary Discover operations, common file and process operations, advisory review when eligible, the Control Center entry point, and the capability-discovery and dispatch operations below.
2. **Discoverable long tail.** Other registered Desktop Commander, Skills, internal Discover, quarantine, and mounted-provider operations remain in the normalized catalogue. They are hidden from the normal `tools/list` response but remain callable through their original server contracts and effect-specific dispatch when eligible.
3. **Status-only records.** Unavailable, disabled, authentication-gated, build-failed, or mount-failed operations remain visible in status and catalogue evidence but are not recommended or dispatched.

Capability user entry points:

- `search_capabilities` ? search normalized Provider, Tool, Discover, Skill, and Workflow contributions and report readiness and eligibility;
- `describe_capability` ? describe one contribution, capability, operation, or workflow with normalized metadata;
- `recommend_workflow` ? rank complete task-level workflows using activation and capability evidence;
- `execute_read_action` ? execute one eligible read-only long-tail operation through its original schema and middleware;
- `execute_change_action` ? execute one eligible local-change, quarantine, or process operation through its original schema and middleware;
- `execute_external_action` ? execute one eligible external operation without bypassing provider readiness or an operation-specific approval requirement.

Scoring is advisory only. Eligibility is evaluated before scoring. Neither intrinsic quality nor contextual suitability can authorize Work, override HR-001, HR-002, or HR-003, bypass approval, weaken original schema validation, or turn an unavailable provider into an operational one. Explicitly requested eligible operations remain reachable through capability search and the matching effect-specific dispatcher.

Provider catalogue membership or mount success does not prove authentication, upstream connectivity, tool discovery, or live verification. Do not add capability profiles, readiness states, scores, or workflow selection as a fourth Work policy rule.

## Errors

Corrective rejection codes are limited to:

- `HR-001_WRITE_OUTSIDE_PROJECTS`;
- `HR-002_EXTERNAL_NETWORK`;
- `HR-003_QUARANTINE_REQUIRED`;
- `HR-003_QUARANTINE_FAILED`;
- versioned `DISCOVER_*` structural path, limit, traversal, read, Git, parse, or output-budget failure;
- other structural input or configuration failure.

HR codes remain exclusive to Work decisions. Discover failures identify the structural reason, field, accepted shape where applicable, and corrective action without being reported as policy violations.

## Verification

Tests must cover:

- path normalization, case handling, prefix collisions, relative paths, links, and junction evidence;
- every known Desktop Commander mutating tool shape and exposed network-consuming contract;
- omitted provider-only network tools and removed provider-only network-mode arguments;
- negative cases proving inert URLs and unknown commands remain allowed;
- direct delete tools, explicit delete operands, `git clean` dry-run, and unresolved permanent-delete handling;
- explicit terminal writes inside and outside `C:\Projects`;
- explicit external package sources, known-client target positions, and locally resolved Git remotes;
- quarantine move, metadata, collision handling, and restoration;
- provider version or schema changes;
- empty provider command-denylist and directory-allowlist invariants;
- startup containment for verified automatic external activity;
- Discover schemas and settings, canonical identity, unsafe links and hard links, bounded traversal and reads, deterministic detection, fixed local Git evidence, pure Python AST indexing, evidence integrity, exact output compaction, donor independence, plane boundaries, and additive tool registration;
- capability contribution completeness, settings weight totals, readiness containment, eligibility before scoring, explainable deterministic ranking, direct-profile bounds, status-only suppression, effect-separated dispatch, instance-scoped runtime state, platform-only gateway imports, and the thin `server.py` fa?ade;
- execution contract/schema identity, backend selection, exact-source/provenance binding, evidence bounds, fail-closed lifecycle outcomes, local-process compatibility, disposable VirtualBox and Hyper-V proof behavior, VirtualBox host/credential/state isolation, and no treatment of unavailable live guest commissioning as a passing result.

Verification must run through the locked external project interpreter, not a globally resolved executable, and must keep caches and generated state beneath `C:\Projects\.kis-mcp`. Verification demonstrates detection quality; it does not create a permission gate for tools outside the three prohibited intents.

## Current implementation boundary

The current implementation includes:

- repository authority, strict JSON configuration, and the closed HR-001/HR-002/HR-003 policy core;
- the Desktop Commander Work adapter, startup containment, provider-contract shaping, quarantine, and restoration;
- local stdio and settings-driven loopback HTTP startup for `operation` and `development`;
- provider-neutral execution request/result/readiness/lifecycle contracts with `local-process` as the primary Actions-independent Windows backend: mutable focused verification remains available, while canonical commit verification materializes a unique detached worktree beneath KIS state, rechecks clean HEAD/tree, executes through the Work boundary under a KIS-owned kill-on-close Windows Job Object, reconciles stale non-terminal runs by cancellation, and emits an immutable hash-bound local verification receipt; disabled-by-default internal `windows-virtualbox-proof` and `windows-hyperv-proof` profiles remain optional clean-room/high-isolation proof providers rather than normal execution prerequisites, and one backend-neutral disposable-verification proof adapter remains available. The VirtualBox provider continues to force KIS-owned global/config/template-media/clone state, pre-start host-integration and network isolation, password-file credentials, exact archive injection through Guest Additions, and recoverable quarantine retirement. Neither disposable Windows provider is treated as live-commissioned by implementation alone;
- public `inspect_project` and bounded local-target `inspect_change` Discover operations for working-tree, staged, commit, range, and branch evidence;
- eleven registered Skills operations backed by the approved shared catalogue, including attributed outcome recording and bounded telemetry reporting, and enriched with capability-bearing runtime cards;
- normalized immutable Provider, Tool, Discover, Skill, Operation, Readiness, Exposure, Quality, and Workflow contracts;
- strict JSON-defined scoring weights, direct-profile limits, and Skills capability metadata;
- deterministic catalogue, readiness, eligibility, explainable scoring, workflow recommendation, and progressive exposure services;
- instance-scoped Provider and capability runtime state with no process-global latest-composition singleton;
- provider-neutral contracts, registry, health, explicit construction, and runtime composition;
- a provider-neutral persistent FastMCP client lifecycle with one outer connection per parent runtime and injectable provider startup bootstrap;
- a strict central project registry with bounded `kis_list_projects` / `kis_project_status` catalogue operations and legacy repository-settings compatibility;
- a disposable repo-local recovery capsule beneath each registered project's own `.temp\\kis` directory, using the shared `EvidenceStore` for immutable worktree-isolated generations containing only typed identity fingerprints, central-generation hints, and hashed idempotency checkpoints; repository/Git/config/provider truth and `C:\\Projects\\.kis-mcp` remain authoritative, and missing/stale/corrupt capsule state is rebuilt rather than trusted;
- seven approval-gated exact registered-GitHub operations for immutable commit publication, tree-equivalent remote-default-rooted review-branch reconciliation, exact-head pull-request creation, merge-commit-only repository landing-policy configuration, canonical registered-Project schema commissioning, exact-head pull-request merge, and exact-head non-default remote-branch deletion, exposed as discoverable virtual operations through `execute_external_action` with exact registered-target and remote-state verification;
- a dormant KIS speculative landing-queue implementation for centrally registered GitHub repositories, retaining read-only status plus approval-gated enqueue/reconcile/dequeue/land operations for diagnostic/history compatibility; it is no longer exposed as a canonical delivery workflow, and its Actions-backed candidate verification does not satisfy repository landing authority;
- `execute_change_workflow` for two-axis verification/review execution using `small|medium|large` complexity plus additive objective risk triggers; verification selection and specialist reviews are bound to the same inspected source fingerprint, completed reviews must prove complete evidence for that exact source, and `review_timeout_ms` bounds the aggregate specialist-review phase; `prepare_reviewable_pull_request` coordinates fixed verified-source-commit → exact-tree reconciliation → deterministic-metadata open-PR preparation and preserves both source and reconciled head SHAs; canonical closeout then executes local verification against the exact current PR head before exact-head merge, remote-branch deletion, or worktree cleanup;
- GitHub MCP using one runtime-scoped client with one `get_me` bootstrap and explicit repository/Project authorization against all registered GitHub bindings, without mutable active-project authorization state;
- Supabase using one persistent account-scoped OAuth client against the unscoped official endpoint, with registered per-call `project_id` validation and targetless read-only discovery only;
- Context7, Control Center, DBHub, Docker Hub MCP, GitHub MCP, Serena, and Supabase adapters available under `context7_*`, `controlcenter_*`, `db_*`, `dockerhub_*`, `github_*`, `serena_*`, and `supabase_*` when enabled adapters build successfully; the checked-in runtime keeps Control Center disabled by default while the other configured backend providers remain enabled; DBHub contributes stable project/binding read operations from one isolated child process per database binding, while Docker Hub remains an external registry connector separate from local Docker Engine/process operations;
- an NVIDIA NIM provider used only by the advisory code-review workflow;
- a generic Tools registry with a pinned Codex CLI `0.147.0` adapter, managed ChatGPT-authenticated home, exact-version/auth readiness, and a read-only mutation-detecting wrapper;
- `review_change_with_agent`, which accepts the same `working_tree|staged|commit|range|branch` source selector as local change inspection, collects deterministic file-aware evidence with explicit included/omitted coverage and the inspected source fingerprint, refuses incomplete evidence before backend invocation, requires a strict structured review result before reporting completion, applies one configured deadline across retries/fallbacks, permits fallback only when backend selection is implicit, supports strict `code-quality`, `safety-security`, `architecture`, `performance`, `test-quality`, `documentation`, and `api-contracts` purposes, and grants no mutation or nested-agent authority;
- provider-neutral Work Management with typed records, documentation-aware actionable intake, exact implementation traceability, atomic review evidence persistence, deterministic reconciliation, attributable portfolio status, repository-owned Project schema/drift evidence, fixed-shape CLI/CI, and bounded task-level platform workflows;
- a bounded GitHub Project adapter plus provider middleware that reads configured Projects, individual fields/items/status updates, adds existing issues or pull requests, permits bounded provider-native batch field updates, preflights revisions, deduplicates source records, and keeps Project/item deletion, Project creation, status-update creation, arbitrary schema administration, and unrestricted GraphQL outside the normal Work surface; the separate approval-gated registered-Project commissioner may create only manifest-declared fields/options/views for an exact central-registry Project binding and must re-read the canonical schema before reporting success;
- pre-merge `project_management_merge_readiness` gate evaluation that requires a passing referenced `source=local` verification result for the exact pull-request head, plus post-merge `project_management_documentation_reconcile` orchestration using the existing `documentation_reconciliation_due` / `post_merge_complete` lifecycle; provider-native GitHub Actions evidence is neither required nor sufficient for landing, and Work Management projects lifecycle state without becoming authoritative for local change creation or Git landing facts;
- pinned AgentSys `6.0.1` and agnix `0.45.0` supervised bootstrap installers with isolated managed paths, staged validation, and recoverable replacement; agnix is additionally available through bounded `validate_agent_configuration` using its ignored repo-local native runtime, while neither component is mounted as a general provider;
- the read-only KIS Control Center MCP App through the explicitly enabled `controlcenter_*` provider or the standalone process; the checked-in gateway composition keeps the UI provider disabled by default.

### Discover status

`inspect_project` returns deterministic local repository evidence for projects beneath `C:\Projects`. It applies JSON-configured retrieval limits, exclusions, text types, encodings, and budgets; rejects unsafe link, reparse, and configured hard-link cases structurally; reads local Git metadata through fixed bounded commands; parses Python with `ast`; discovers verification commands without executing them; and performs no network access or repository-code execution.

For registered projects with Discover memory enabled, the central Discover `EvidenceStore` generation remains the reusable evidence authority. After that central generation is successfully created or reused, Discover publishes a small recovery hint to `<registered local_root>\.temp\kis` under a namespace derived from the active worktree. The hint records only fixed-schema identity fingerprints and the verified central generation ID. A local hint never makes an otherwise stale central generation current, and failure to read or write the local capsule degrades diagnostics only; it does not change Discover correctness.

The public local-evidence surface exposes `inspect_project`, bounded local-target `inspect_change` for working-tree, staged, commit, range, and branch evidence, `get_code_context`, and `analyze_change`; read-only `plan_change` composes that evidence as the Work-planning bridge. Context brokering may retain bounded support artifacts related to selected implementation evidence. Impact analysis includes direct and bounded transitive Python import dependants, bounded JavaScript/TypeScript dependency evidence, affected tests and verification handoffs, and advisory contract/documentation/configuration/policy relationships. `plan_change` reports planned paths, an evidence fingerprint, active-claim conflicts, and `REUSE`/`EXTEND`/`REPLACE`/`NEW` repository-pattern guidance; `analyze_change` may reconcile optional planned paths against actual scope and reports deleted/renamed replacement candidates only when remaining reference evidence exists. These outputs are Discover evidence and recommendations only: they do not implement Govern, authorize deletion, execute verification, or add a Work-policy decision.

### Provider and agent status

The Provider registry contains nine descriptors: Control Center, Desktop Commander, Context7 MCP, DBHub, Docker Hub MCP, GitHub MCP, NVIDIA NIM, Serena MCP, and Supabase. Runtime JSON contains seven namespaced provider records: Context7, Control Center, DBHub, Docker Hub MCP, GitHub, Serena, and Supabase. Control Center is disabled by default; the other six are enabled for gateway mounting. DBHub uses the source-aware connector boundary and one isolated child process per registered binding; the exact pinned `v1.2.0` installation is commissioned, and the checked-in College `results` SQLite binding is live-verified for `search_objects` plus read-only `execute_sql`. Docker Hub remains separate from local Docker Engine operations and is commissioned at the exact approved source revision in credential-free public mode. Its KIS public surface exposes the six currently live-verified repository/tag read operations; upstream `search` remains intentionally hidden because the pinned provider's declared output schema rejects Docker Hub's current `search_after` response field. Successful DBHub/Docker Hub live commissioning persists exact-identity evidence beneath the configured KIS state root; a later runtime may report that historical live verification without claiming that its current child process has re-established upstream connection or tool discovery. Adapter build, invalid-result, mount, authentication, current-process readiness, and historical commissioning remain separate; one unavailable optional provider does not prevent Work, Discover, Skills, agent registration, or gateway startup.

GitHub construction owns one shared FastMCP `Client` for each parent KIS runtime. The provider lifecycle connects it once, performs one `get_me` bootstrap after connection, reuses that authenticated process across downstream sessions, and closes it only when that parent runtime stops. Restarting `kis-op` or `kis-dev` creates a new provider process for that instance and therefore requires one new OAuth sign-in for the restarted runtime. Gateway composition loads one immutable central project registry and GitHub middleware authorizes explicit repository and Project coordinates against its registered union on every call.

Supabase uses the same provider-neutral persistent lifecycle without a provider-specific startup call. It authenticates once against the unscoped account endpoint, discovers the runtime tool surface, and reuses that connection until parent shutdown. Project-targeted operations require an explicit registered Supabase `project_id`; targetless operations require upstream read-only annotation. `kis_provider_status` keeps account authentication/tool discovery separate from explicit registered-project commissioning evidence. NVIDIA is not mounted as a general passthrough. Codex CLI is a local executable Tool adapter, not a Provider-module connector.

`review_change_with_agent` accepts the same local Git source selector as `inspect_change`: `working_tree`, `staged`, `commit`, `range`, or `branch`, with the required target refs for non-working-tree sources. Discover is the source-identity authority: mutable selectors are resolved internally to exact Git object IDs, fingerprints bind working-tree/staged content or immutable commit/range identities rather than only path/status metadata, and review evidence commands use those resolved identities. The evidence collector packages whole changed-file sections plus repository `AGENTS.md` under the configured character budget, rechecks the selected source after packaging, and returns the source fingerprint together with included/omitted file coverage. Evidence is complete only when source inspection remains stable and every required file/instruction section is represented; incomplete evidence returns a typed non-success result before any review backend is invoked. Successful review output must be one strict JSON object containing a non-empty `summary`, structurally valid `findings`, and string-list `unknowns`; malformed, schema-invalid, or over-budget output is never reported as completed. `review_deadline_seconds` in `settings/agents/code-review-agent.settings.json` is one total deadline across the review's backend attempts, retries, and implicit fallback, and each backend invocation receives only the remaining budget. `execute_change_workflow` independently binds completed specialist-review evidence to the same source fingerprint returned by verification selection, rejects fingerprint mismatch/incomplete evidence, and bounds the whole specialist-review phase with `review_timeout_ms`. The reviewer selects NVIDIA NIM or Codex CLI, permits at most one fallback only when backend selection is implicit, and accepts exactly one of `code-quality` (default), `safety-security`, `architecture`, `performance`, `test-quality`, `documentation`, or `api-contracts`; every purpose retains the no-mutation/no-nested-delegation boundary. Explicit `backend="codex-cli"` invokes only Codex. NVIDIA remains one backend with exactly three selectable aliases: `nano` for fast/focused review, `super` as the default substantive review profile, and `ultra` for deepest/high-impact analysis. Supplying a model explicitly selects NVIDIA; supplying an NVIDIA model with `codex-cli` is invalid. Successful NVIDIA results report only the selected alias and exact model ID as provenance, not reasoning traces or credentials. `scripts/start-chatgpt.ps1` reads the current-user verified runtime unlock from Windows Credential Manager without prompting, resolves `secret://provider/nvidia-nim/api-key` through the encrypted application vault, and injects the key only as process-scoped `NVIDIA_API_KEY` for the selected server child. Vault mutation remains interactive. Codex receives the prompt through standard input via `scripts/invoke-codex-agent.ps1`, uses the pinned managed `CODEX_HOME`, removes API-key override variables, requests an ephemeral read-only sandbox, and fails if its before/after Git-visible repository fingerprint changes. Codex readiness requires exact version `0.147.0` and ChatGPT authentication of that managed profile.

### Work-management status

The work-management domain remains provider-neutral and does not import FastMCP or GitHub layouts. It is an operational projection over authoritative local change records and Git/GitHub landing facts, not a prerequisite authority for creating a governed change. Platform composition adds eight bounded task-level tools when strict work-management settings are enabled: inventory, reconciliation, Project schema status, merge readiness, documentation reconciliation, portfolio status, review-evidence persistence, and traceability verification. Task-level workflow descriptors compose those operations; the Actions-backed merge-queue completion descriptor is no longer canonical. The checked-in configuration manages `kis-mcp`, `chatgpt-skill`, `commodity`, `college`, and `import-isolate` through the shared user Project #1 backend. The Project coordinate is registered once through `kis-mcp`; each managed repository retains its own central-registry repository identity and maps to the stable `github-default` Work Management binding. Feature, gate, automation, and evidence modes remain owned by work-management settings, and existing backend-binding IDs remain stable for compatibility.

`settings/work-management/github-project-schema.json` remains the repository-owned desired operational projection: **25 managed fields and 12 named views with executable semantics**. Each managed view declares its layout, filter, visible-field order, sort/group configuration, and board vertical grouping. The configured canonical manifest requires exactly 12 views, a non-empty current `Status` single-select, and exactly one `status:` qualifier per view containing only current canonical Status values; explicit alternate manifest files retain the generic parser contract. Legacy `Todo` / `In Progress` values may remain as unmanaged Project state but cannot be admitted by a canonical view filter. `Module` is free-form text rather than an empty single-select, because GitHub cannot create or use a single-select without at least one option. `Blocked By` is a text field because queue admission must distinguish an explicitly observed empty dependency value from unavailable dependency evidence. Empty GitHub Project field entries normalize to `null`; field metadata such as the field name is never treated as the field value. `Complexity` and `Risk Triggers` project the authoritative change classification without replacing existing work identity, priority, severity, or lifecycle fields. `project_management_schema_status` compares official GitHub MCP field inventory plus the bounded registered-Project view inventory with that manifest deterministically; filtered canonical views also require complete bounded saved-view item readback, and missing, malformed, incomplete, semantically mismatched, or behaviorally contradictory evidence keeps `views_ready=false`. The normal GitHub MCP surface continues to own Project/item reads and bounded item-field updates. Schema provisioning is isolated to `kis_github_commission_registered_project_schema`, which resolves an exact central-registry Project binding, uses only the canonical manifest, preserves existing single-select option IDs when extending options, refuses incompatible field types or unsupported existing-view semantic mutations, updates API-supported view semantics in place, creates no deletion/recreate path, and requires a fresh structural and behavioral re-read before returning `ready=true`. Arbitrary schema administration, native Project workflow configuration, Project/item deletion, Project creation, status-update creation, and unrestricted GraphQL remain outside the approved KIS surface.

Local review evidence is persisted only beneath `.work/reviews/<review-id>/` using bounded atomic replacement and conflict detection. Remote reconciliation defaults to preview and requires explicit apply plus an idempotency key. Safe create checks observed Project items for the same source issue or pull request before mutation, so restart does not duplicate records. Pre-merge readiness consumes exact PR/head evidence plus the Work projection and requires a passing referenced local verification result at the exact head; Actions-only, stale, failed, or unreferenced verification fails closed. After confirmed merge evidence, an operator or governing workflow may invoke `project_management_documentation_reconcile` to create/apply `documentation_reconciliation_due`; required documentation work remains in `Documentation` until a later invocation records `post_merge_complete` at an exact completion revision. Provider absence, unsupported methods, stale revisions, inaccessible state, incomplete pagination, and registry/work-management identity conflicts are corrective work-management outcomes rather than HR policy violations.

Current live commissioning status belongs to `docs/OPERATIONS.md`; dated evidence is retained in the applicable change/issue closeout records. Repository implementation now includes bounded schema/view commissioning rather than treating missing provider primitives as a permanent gap. Repository and Project authorization are validated through registered GitHub coordinates; historical repository-local routing settings remain compatibility data and do not widen those registered coordinates.

### Remote and standalone status

Both remote instance records contain distinct configured tunnel IDs and loopback ports. That configuration does not prove the Windows credential exists, a profile has been generated, the external tunnel is connected, ChatGPT has scanned the catalogue, or end-to-end operations have passed. External commissioning requires those separate supervised checks.

The KIS Control Center can run independently with `python -m kis_mcp.control_center` and is also mounted under `controlcenter_*` when enabled in provider-runtime settings. Both forms expose the same read-only evidence model. The mounted form receives the owning gateway instance's provider status explicitly; no process-global latest-composition state is used. Standalone rendering reports runtime mount state as unavailable rather than inferring zero mounted providers when no owning gateway status source is attached.

The remote runtime starts FastMCP with the checked-in `stateless_http=true` and JSON-response settings; startup and transport regression coverage keep the executable mode aligned with configuration. `kis_health` also returns a process-stable `server_instance_id`, `server_started_at`, source revision, contract fingerprint, selected runtime identity, and transport flags so two calls can be proven to target the same running process and public contract. Runtime observability retains only bounded correlation metadata for `initialize`, `tools/list`, and `tools/call` plus existing tool-call key names and policy outcomes; it never retains prompt text, argument values, result bodies, or credentials. The Control Center exposes that bounded boundary evidence for supervised connection diagnosis.

None of these implementation-status statements restrict normal Work beyond HR-001, HR-002, and HR-003.
