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

The repository does not contain an inherited SDK2 runtime, a custom replacement filesystem or terminal, a capability-profile permission framework, a governance subsystem, or a fork of Desktop Commander. It implements bounded Discover, Skills, Provider, Tools, workflow, and Control Center modules natively under `src/kis_mcp`; donor repositories remain source evidence only and are not runtime dependencies. Repository-local `.agents/skills` material remains procedural development guidance. The runtime Skills module resolves reusable procedures exclusively from the operator-approved shared root `C:\\Projects\\.agents\\skills` through `settings/skills.settings.json`, and its mutations re-enter the existing Work middleware and Desktop Commander backend.

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
| Standalone | KIS Control Center read-only MCP App and UI resource. |
| Managed support tooling | AgentSys `6.0.1` host profiles and agnix `0.45.0` are installed through supervised bootstrap scripts beneath `C:\Projects`. Agnix uses the operator-approved ignored repo-local runtime path `C:\Projects\kis-mcp\.temp\tools\agnix\0.45.0` for Windows application-control compatibility and is exposed only through bounded `validate_agent_configuration`; neither tool is mounted as a general provider. |
| Target | Govern operations, broader semantic and trusted remote evidence, and additional executable workflow orchestration. |

The future platform model does not alter the closed Work enforcement decision set. Profiles, catalogues, governance findings, evidence requirements, readiness, or workflow selection must not become additional reasons to block an otherwise permitted invocation.

## Components

| Component | Responsibility |
|---|---|
| Desktop Commander | Provides ordinary filesystem, edit, search, process, testing, and local-development tools. |
| FastMCP gateway | Composes domain platform entry points, owns instance-scoped capability and readiness state, presents the curated tool surface, evaluates concrete Work invocations, and forwards allowed calls through original contracts. |
| Discover module | Exposes bounded `inspect_project`, `inspect_change`, `get_code_context`, and `analyze_change`; all share one registered-project intelligence service that persists bounded Code Atlas, Symbol Atlas, and Relationship Graph generations with freshness/fingerprint/provenance metadata and deterministic local fallback. |
| Skills module | Resolves the approved shared catalogue, overlays reviewed category and capability metadata, contributes Skills to the normalized catalogue, and routes create/improve mutations back through Work middleware. |
| Provider runtime | Registers Desktop Commander, Context7 MCP, GitHub MCP, NVIDIA NIM, Serena MCP, Supabase, and Control Center descriptors; mounts enabled connectors under unique namespaces; keeps Context7 independent from project memory; exposes Serena only through a read-only semantic surface with offline-enforced startup; owns runtime-scoped provider clients; contains failures; and reports readiness and commissioning separately. |
| Capability composition | Normalizes Provider, Tool, Discover, Skill, and Workflow contributions; evaluates readiness and eligibility; scores explainable recommendations; and plans direct, discoverable, or status-only exposure. |
| Tools and workflows | Registers local executable adapters such as Codex CLI, contributes normalized operations, describes complete user workflows, exposes bounded advisory code review with NVIDIA/Codex backend selection, and exposes pinned agnix validation through fixed read-only arguments with no fix authority. |
| Managed bootstrap tooling | Installs pinned Codex CLI, AgentSys, and agnix distributions beneath `C:\Projects`, creates isolated managed profiles, validates staged state, and preserves replaced state through quarantine without expanding Work authority. |
| Control Center | Provides a read-only MCP App and UI resource through the mounted `controlcenter_*` provider and through the standalone process; it does not authorize Work mutations. |
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
- `settings.discover` defines the enable flag, exclusions, text types, encodings, hard-link behavior, file/directory/Git/index/output budgets, and the strict persistent-intelligence block: central state root, schema version, stored-byte/file/module/symbol/relationship limits, fingerprint fields, provider inclusion, corruption handling, and recoverable supersession behavior.
- `settings/providers/platform-runtime.provider.json` selects exactly the approved mounted MCP provider IDs, records runtime enablement, and assigns unique lower-case namespaces. It contains no credentials.
- `settings/providers/context7.provider.json` pins the independent Context7 external-documentation MCP installation and launch contract; it is not a Discover project-memory source.
- `settings/providers/serena.provider.json` pins Serena `1.6.1`, the relocatable venv-interpreter launch contract, contained provider state roots, and semantic-provider identity. Runtime startup enforces `UV_OFFLINE=1` and rewrites Serena's own global `project_serena_folder_location` to the JSON-governed central template `C:\\Projects\\.kis-mcp\\serena\\projects\\$projectFolderName\\.serena` before activation. KIS pre-creates that central path and binds each folder name to one normalized project root with a JSON identity marker, failing on collisions rather than sharing state. Repo-local `.serena` generation is not permitted; Serena memory files remain provider-managed state, not KIS project memory.
- `settings/providers/github-mcp.provider.json` contains only GitHub provider identity, pinned executable/source, OAuth mode, PAT-conflict metadata, and toolsets. Repository and GitHub Project routing are not provider-authentication settings.
- `settings/projects.settings.json` is the strict central project registry. It maps stable project IDs to absolute local roots and optional GitHub repository, GitHub Project, and Supabase routing coordinates without storing credentials.
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

The implemented Skills module resolves one reusable procedure catalogue from `C:\Projects\.agents\skills`. It builds a deterministic immutable snapshot after validating `SKILL.md` frontmatter, file paths, configured suffixes, encodings, links, sizes, and limits. Repository-local `.agents/skills` is not part of this runtime catalogue.

The module exposes bounded list, search, load, file-search, file-read, refresh, structural-evaluation, create, and improve operations. Runtime cards are enriched from `settings/capabilities.settings.json` so every current shared Skill has a non-empty category, capability set, activation terms, effects, and workflow roles. ChatGPT loads the returned instructions and executes their workflows through ordinary kis-mcp Work tools; the server does not import or automatically execute arbitrary skill code.

Skill creation validates a complete proposed entrypoint, stages it beneath `C:\Projects\.kis-mcp\temp\skills`, and publishes it with Desktop Commander `create_directory`, `write_file`, and `move_file`. Skill improvement requires the active file SHA-256 and uses Desktop Commander `edit_block` with one exact expected replacement. Every mutation calls `FastMCP.call_tool(..., run_middleware=True)`, so the existing three-rule middleware evaluates the concrete Work effects.

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
- capability contribution completeness, settings weight totals, readiness containment, eligibility before scoring, explainable deterministic ranking, direct-profile bounds, status-only suppression, effect-separated dispatch, instance-scoped runtime state, platform-only gateway imports, and the thin `server.py` fa?ade.

Verification must run through the locked external project interpreter, not a globally resolved executable, and must keep caches and generated state beneath `C:\Projects\.kis-mcp`. Verification demonstrates detection quality; it does not create a permission gate for tools outside the three prohibited intents.

## Current implementation boundary

The current implementation includes:

- repository authority, strict JSON configuration, and the closed HR-001/HR-002/HR-003 policy core;
- the Desktop Commander Work adapter, startup containment, provider-contract shaping, quarantine, and restoration;
- local stdio and settings-driven loopback HTTP startup for `operation` and `development`;
- public `inspect_project` and working-tree `inspect_change` Discover operations;
- nine registered Skills operations backed by the approved shared catalogue and enriched with capability-bearing runtime cards;
- normalized immutable Provider, Tool, Discover, Skill, Operation, Readiness, Exposure, Quality, and Workflow contracts;
- strict JSON-defined scoring weights, direct-profile limits, and Skills capability metadata;
- deterministic catalogue, readiness, eligibility, explainable scoring, workflow recommendation, and progressive exposure services;
- instance-scoped Provider and capability runtime state with no process-global latest-composition singleton;
- provider-neutral contracts, registry, health, explicit construction, and runtime composition;
- a provider-neutral persistent FastMCP client lifecycle with one outer connection per parent runtime and injectable provider startup bootstrap;
- a strict central project registry with bounded `kis_list_projects` / `kis_project_status` catalogue operations and legacy repository-settings compatibility;
- five approval-gated exact registered-GitHub operations for immutable commit publication, tree-equivalent remote-default-rooted review-branch reconciliation, exact-head pull-request creation, exact-head pull-request merge, and exact-head non-default remote-branch deletion, exposed as discoverable virtual operations through `execute_external_action` with exact remote-state verification;
- `execute_change_workflow` for bounded verification/review execution and `prepare_reviewable_pull_request` for fixed verified-source-commit → exact-tree reconciliation → exact open-PR coordination; completion preserves both source and reconciled head SHAs and intentionally stops before merge, remote-branch deletion, or worktree cleanup;
- GitHub MCP using one runtime-scoped client with one `get_me` bootstrap and explicit repository/Project authorization against all registered GitHub bindings, without mutable active-project authorization state;
- Supabase using one persistent account-scoped OAuth client against the unscoped official endpoint, with registered per-call `project_id` validation and targetless read-only discovery only;
- GitHub MCP and Supabase adapters mounted under `github_*` and `supabase_*` when enabled adapters build successfully;
- an NVIDIA NIM provider used only by the advisory code-review workflow;
- a generic Tools registry with a pinned Codex CLI `0.147.0` adapter, managed ChatGPT-authenticated home, exact-version/auth readiness, and a read-only mutation-detecting wrapper;
- `review_change_with_agent`, which collects bounded local evidence, permits one fallback only when backend selection is implicit, supports strict `code-quality`, `safety-security`, `architecture`, `performance`, `test-quality`, `documentation`, and `api-contracts` purposes, and grants no mutation or nested-agent authority;
- provider-neutral P0-P5 work management with typed records, exact implementation traceability, atomic review evidence persistence, deterministic reconciliation, attributable portfolio status, fixed-shape CLI/CI, and five task-level platform workflows;
- a bounded GitHub Project adapter that reads configured Projects, adds existing issues or pull requests, updates explicit fields, preflights revisions, deduplicates source records, and exposes no delete or unrestricted GraphQL operation;
- pinned AgentSys `6.0.1` and agnix `0.45.0` supervised bootstrap installers with isolated managed paths, staged validation, and recoverable replacement; agnix is additionally available through bounded `validate_agent_configuration` using its ignored repo-local native runtime, while neither component is mounted as a general provider;
- the read-only KIS Control Center MCP App through the mounted `controlcenter_*` provider and the standalone process.

### Discover status

`inspect_project` returns deterministic local repository evidence for projects beneath `C:\Projects`. It applies JSON-configured retrieval limits, exclusions, text types, encodings, and budgets; rejects unsafe link, reparse, and configured hard-link cases structurally; reads local Git metadata through fixed bounded commands; parses Python with `ast`; discovers verification commands without executing them; and performs no network access or repository-code execution.

The public local-evidence surface exposes `inspect_project`, bounded local-target `inspect_change`, `get_code_context`, and `analyze_change`; read-only `plan_change` composes that evidence as the Work-planning bridge. Context brokering may retain bounded support artifacts related to selected implementation evidence. Impact analysis includes direct and bounded transitive Python import dependants, bounded JavaScript/TypeScript dependency evidence, affected tests and verification handoffs, and advisory contract/documentation/configuration/policy relationships. `plan_change` reports planned paths, an evidence fingerprint, active-claim conflicts, and `REUSE`/`EXTEND`/`REPLACE`/`NEW` repository-pattern guidance; `analyze_change` may reconcile optional planned paths against actual scope and reports deleted/renamed replacement candidates only when remaining reference evidence exists. These outputs are Discover evidence and recommendations only: they do not implement Govern, authorize deletion, execute verification, or add a Work-policy decision.

### Provider and agent status

The Provider registry contains Desktop Commander, GitHub MCP, NVIDIA NIM, and Supabase descriptors. Runtime JSON selects GitHub and Supabase for deterministic namespaced mounting. Adapter build, invalid-result, mount, authentication, and commissioning states remain separate; one unavailable optional provider does not prevent Work, Discover, Skills, agent registration, or gateway startup.

GitHub construction owns one shared FastMCP `Client` for the parent `kis-op` runtime. The provider lifecycle connects it once, performs one `get_me` bootstrap after connection, reuses that authenticated process across downstream sessions, and closes it only when the parent runtime stops. Restarting `kis-op` creates a new provider process and therefore requires one new OAuth sign-in. Gateway composition loads one immutable central project registry and GitHub middleware authorizes explicit repository and Project coordinates against its registered union on every call.

Supabase uses the same provider-neutral persistent lifecycle without a provider-specific startup call. It authenticates once against the unscoped account endpoint, discovers the runtime tool surface, and reuses that connection until parent shutdown. Project-targeted operations require an explicit registered Supabase `project_id`; targetless operations require upstream read-only annotation. `kis_provider_status` keeps account authentication/tool discovery separate from explicit registered-project commissioning evidence. NVIDIA is not mounted as a general passthrough. Codex CLI is a local executable Tool adapter, not a Provider-module connector.

`review_change_with_agent` collects bounded `AGENTS.md`, Git status, staged diff, and unstaged diff evidence. It selects NVIDIA NIM or Codex CLI, permits at most one fallback only when backend selection is implicit, and accepts exactly one of `code-quality` (default), `safety-security`, `architecture`, `performance`, `test-quality`, `documentation`, or `api-contracts`. Each purpose changes only the review rubric applied to the same bounded evidence and backend contract; the operation still exposes no mutation or nested delegation authority. Explicit `backend="codex-cli"` invokes only Codex. NVIDIA remains one backend with exactly three selectable aliases: `nano` for fast/focused review, `super` as the default substantive review profile, and `ultra` for deepest/high-impact analysis. Supplying a model explicitly selects NVIDIA; supplying an NVIDIA model with `codex-cli` is invalid. Successful NVIDIA results report only the selected alias and exact model ID as provenance, not reasoning traces or credentials. `scripts/start-chatgpt.ps1` reads the current-user verified runtime unlock from Windows Credential Manager without prompting, resolves `secret://provider/nvidia-nim/api-key` through the encrypted application vault, and injects the key only as process-scoped `NVIDIA_API_KEY` for the selected server child. Vault mutation remains interactive. Codex receives the prompt through standard input via `scripts/invoke-codex-agent.ps1`, uses the pinned managed `CODEX_HOME`, removes API-key override variables, requests an ephemeral read-only sandbox, and fails if its before/after Git-visible repository fingerprint changes. Codex readiness requires exact version `0.147.0` and ChatGPT authentication of that managed profile.

### Work-management status

The work-management domain remains provider-neutral and does not import FastMCP or GitHub layouts. Platform composition adds five task-level tools when strict work-management settings are enabled. The checked-in configuration is enabled for the `kis-mcp` user Project #1 binding. Feature, gate, automation, and evidence modes remain owned by work-management settings; managed-project local/GitHub identity and Project coordinates are reconciled from the central registry, while existing backend-binding IDs remain stable for compatibility.

Local review evidence is persisted only beneath `.work/reviews/<review-id>/` using bounded atomic replacement and conflict detection. Remote reconciliation defaults to preview and requires explicit apply plus an idempotency key. Safe create checks observed Project items for the same source issue or pull request before mutation, so restart does not duplicate records. Provider absence, unsupported methods, stale revisions, inaccessible state, incomplete pagination, and registry/work-management identity conflicts are corrective work-management outcomes rather than HR policy violations.

Live work-management commissioning remains deployment evidence rather than an implementation inference. Repository and Project authorization are now validated through registered GitHub coordinates; historical repository-local routing settings remain compatibility data and do not widen those registered coordinates.

### Remote and standalone status

Both remote instance records contain distinct configured tunnel IDs and loopback ports. That configuration does not prove the Windows credential exists, a profile has been generated, the external tunnel is connected, ChatGPT has scanned the catalogue, or end-to-end operations have passed. External commissioning requires those separate supervised checks.

The KIS Control Center can run independently with `python -m kis_mcp.control_center` and is also mounted under `controlcenter_*` when enabled in provider-runtime settings. Both forms expose the same read-only evidence model. The mounted form receives the owning gateway instance?s provider status explicitly; no process-global latest-composition state is used.

The remote runtime starts FastMCP with the checked-in `stateless_http=true` and JSON-response settings; startup and transport regression coverage keep the executable mode aligned with configuration.

None of these implementation-status statements restrict normal Work beyond HR-001, HR-002, and HR-003.
