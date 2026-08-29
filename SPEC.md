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

The current gateway implements Work, bounded Discover with persistent registered-project intelligence, Skills, Provider and Tool composition, a normalized capability catalogue, readiness-aware progressive exposure, first-class workflow descriptors and recommendations, effect-specific long-tail dispatch, quarantine operations, and one executable advisory code-review workflow. Discover persists bounded derived Code Atlas, Symbol Atlas, and Relationship Graph generations beneath canonical project/source reconstructible-cache namespaces in the central KIS state root and may enrich them with optional normalized Serena semantics; repository/Git/document evidence remains authoritative. Govern remains target-state work.

### Capability exposure

| Exposure | Current capability |
|---|---|
| Direct gateway profile | A JSON-bounded set of frequent Desktop Commander, gateway, Discover, advisory-review, capability-discovery, effect-specific dispatch, and Control Center entry points. Only eligible ready or degraded operations enter the normal direct surface. |
| Discoverable long tail | Remaining registered Desktop Commander, Skills, internal Discover, quarantine, and namespaced provider operations. They retain original schemas and middleware, are searchable by capability, and may be invoked through effect-specific dispatch when eligible. |
| Status-only | Disabled, unavailable, authentication-gated, build-failed, or mount-failed operations remain visible through provider and capability status but are not normally exposed or recommended. |
| Standalone | KIS Control Center read-only MCP App and UI resource. It remains available as an explicit operator-launched surface, while the default gateway provider composition keeps it disabled. |
| Managed support tooling | AgentSys `6.0.1` host profiles and agnix `0.45.0` are installed through supervised bootstrap scripts beneath `C:\Projects`. Agnix is KIS-owned generated tooling at `C:\Projects\.kis-mcp\tools\agnix\0.45.0`: the bootstrap reacquires the exact upstream Linux x86_64 release asset from `agent-sh/agnix`, verifies its published SHA-256 sidecar, smoke-tests it in the configured WSL2 Ubuntu distribution, and only then promotes it. `validate_agent_configuration` invokes that pinned Linux binary through `wsl.exe`; Node/npm are not part of the runtime path, and agnix is not mounted as a general provider. |
| Target | Govern operations, broader semantic and trusted remote evidence, and additional executable workflow orchestration. |

The future platform model does not alter the closed Work enforcement decision set. Profiles, catalogues, governance findings, evidence requirements, readiness, or workflow selection must not become additional reasons to block an otherwise permitted invocation.

## Components

| Component | Responsibility |
|---|---|
| Desktop Commander | Provides ordinary filesystem, edit, search, process, testing, and local-development tools. |
| FastMCP gateway | Runs on pinned FastMCP 4, composes domain platform entry points, owns instance-scoped capability and readiness state, presents the curated tool surface, evaluates concrete Work invocations, forwards allowed calls through original contracts, and exposes MCP Tasks for selected long-running operations without making connection/session state authoritative. |
| Discover module | Exposes bounded `inspect_project`, `inspect_change`, `get_code_context`, and `analyze_change`; all share one registered-project intelligence service that persists bounded Code Atlas, Symbol Atlas, and Relationship Graph generations in canonical project/source reconstructible-cache namespaces with freshness/fingerprint/provenance metadata and deterministic local fallback. |
| Skills module | Resolves the approved shared catalogue, overlays reviewed category and capability metadata, contributes Skills to the normalized catalogue, routes create/improve mutations back through Work middleware, and records bounded redacted usage/outcome telemetry for downstream evaluation. |
| Provider runtime | Registers Desktop Commander, Context7 MCP, DBHub, Docker Hub MCP, GitHub MCP, NVIDIA NIM, Serena MCP, and Control Center in normal composition; mounts enabled connectors under unique namespaces; keeps Context7 independent from project memory; exposes Serena only through a read-only semantic surface with offline-enforced startup; creates one isolated DBHub proxy per registered database binding; keeps Docker Hub separate from local Docker Engine operations; owns runtime-scoped provider clients; contains failures; and reports readiness and commissioning separately. Supabase implementation/configuration remains parked in the repository but is deliberately absent from normal provider, capability, status, and tool surfaces until a future operator-approved activation. |
| Capability composition | Normalizes Provider, Tool, Discover, Skill, and Workflow contributions; evaluates readiness and eligibility; scores explainable recommendations; and plans direct, discoverable, or status-only exposure. |
| Tools and workflows | Registers local executable adapters such as Codex CLI, contributes normalized operations, describes complete user workflows, exposes bounded advisory code review with NVIDIA/Codex backend selection, and exposes pinned agnix validation through fixed read-only arguments with no fix authority. |
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

### MCP 2026 request and task boundary

The FastMCP 4 boundary follows MCP 2026-07-28 stateless request semantics where the client/runtime supports them. Protocol version, client identity, and client capabilities are request-scoped metadata; KIS does not derive durable ownership, authorization, or Work identity from a connection or FastMCP session. `server/discover` is the modern discovery boundary. `initialize` is retained only as dual-era legacy compatibility/observability, not as modern authority.

Selected long-running operations (`run_verification`, `review_change_with_agent`, `kis_post_merge_commissioning_run`, `prepare_reviewable_pull_request`, and `converge_change_to_done`) use optional `io.modelcontextprotocol/tasks` execution. A client that advertises Tasks may receive a `resultType: "task"` handle and later retrieve the terminal result by task ID after reconnecting to the same running KIS service. A client that does not advertise Tasks uses the ordinary synchronous tool result. MCP task IDs are transport-facing handles only; existing KIS Work records, execution identities, receipts, and fencing remain authoritative. `converge_change_to_done` consumes a persisted `PromotionReady` handoff and uses the durable KIS `PromotionController` checkpoint as the sole resume authority for the ordered promotion stages; completed stages and their observations survive request/task interruption and are not replayed merely because MCP task state is lost.

Foreground request timeout, KIS execution deadline, execution stall detection, and MCP task TTL are separate. Verification reports monotonic bounded progress, retains a maximum execution deadline, and attempts cooperative termination when it owns a live child-process PID and the request/task is cancelled or times out. Cancellation intent does not itself rewrite durable KIS Work state to `cancelled`.

FastMCP's current default task backend is process-local. Client transport loss/reconnect is supported and tested; persistence of MCP task state across a KIS server-process restart is not claimed. Durable KIS execution/receipt state remains recoverable independently of MCP task storage.

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
- `settings/providers/platform-runtime.provider.json` retains the configured provider records and unique lower-case namespaces without credentials. Normal composition deliberately suppresses the parked `supabase` record until a future operator-approved activation, so the retained setting is not evidence of runtime exposure.
- `settings/providers/context7.provider.json` pins the independent Context7 external-documentation MCP installation and launch contract; it is not a Discover project-memory source.
- `settings/providers/dbhub.provider.json` pins the DBHub source/release identity, stdio entry point, generated-state root, row bound, and the read-only `search_objects` / `execute_sql` tool set. KIS generates one runtime TOML and one isolated DBHub child proxy per registered database binding; external DSNs are resolved only into process-scoped environment state.
- `settings/providers/dockerhub.provider.json` pins the official Docker Hub MCP source revision, stdio entry point, and public-or-PAT authentication metadata. Public mode stores no credential reference; PAT mode stores only a canonical vault reference and username, and the child receives only `HUB_PAT_TOKEN`.
- `settings/providers/serena.provider.json` pins Serena `1.6.1`, the relocatable venv-interpreter launch contract, contained provider state roots, and semantic-provider identity. Runtime startup enforces `UV_OFFLINE=1` and rewrites Serena's own global `project_serena_folder_location` to the JSON-governed central template `C:\\Projects\\.kis-mcp\\serena\\projects\\$projectFolderName\\.serena` before activation. KIS pre-creates that central path and binds each folder name to one normalized project root with a JSON identity marker, failing on collisions rather than sharing state. Repo-local `.serena` generation is not permitted; Serena memory files remain provider-managed state, not KIS project memory.
- `settings/providers/github-mcp.provider.json` contains only GitHub provider identity, pinned executable/source, OAuth mode, PAT-conflict metadata, and toolsets. Repository and GitHub Project routing are not provider-authentication settings.
- `settings/projects.settings.json` is the strict central project registry. It maps stable project IDs to absolute local roots and optional GitHub repository, GitHub Project, Supabase, database, and Docker Hub routing coordinates without storing credential values. Local database bindings use relative SQLite paths with no secret; external database bindings use only canonical `secret://...` references; Docker Hub project bindings store only non-secret namespaces.
- `settings/work-management/contracts/` contains the three Work-specific canonical machine-readable authorities for item/vocabulary/applicability semantics, lifecycle/operation semantics, and selection semantics. `settings/work-management/github-projects.settings.json` owns Work Management feature, gate, evidence, and backend-binding behavior; `settings/work-management/command-plane.settings.json` is a compatibility/runtime projection validated against the canonical contracts; `settings/work-management/github-project-schema.json` owns the desired **28-field / 12-view** GitHub Project projection and is likewise validated against canonical field/type/option semantics.
- `settings.github_cli.config_dir` is the non-secret GitHub CLI authentication-state directory used only by KIS exact registered-repository mutations. It must resolve beneath `C:\\Projects`, remain outside the repository, and is passed to `gh`/Git only as process-scoped `GH_CONFIG_DIR`; KIS never reads or stores the credential value.
- `settings/kis-repository.settings.json` remains a legacy compatibility source for callers that explicitly use the repository-settings loader; gateway composition uses the central registry-backed selector instead.
- `settings/agents/code-review-agent.settings.json` defines the single advisory code-review agent, its NVIDIA NIM and Codex CLI backends, preferred/fallback order, evidence/output budgets, the canonical NVIDIA vault reference, exactly three NVIDIA profiles (`nano`, `super`, `ultra`) with `super` as default, and the pinned Codex executable/home/version. It stores no NVIDIA or Codex credential value. `settings/bootstrap/codex.install.json` separately pins exact `@openai/codex@0.147.0`, ChatGPT authentication mode, and all managed install/cache/home/quarantine paths beneath `C:\Projects`.
- `settings/secrets.settings.json` defines the encrypted application-vault metadata plus the non-secret Windows Credential Manager target used for the verified runtime unlock. Ordinary startup reads that current-user credential non-interactively; vault initialization, secret mutation, master-key rotation, and one-time existing-vault migration remain supervised operations.
- `settings.remote_mcp` defines the loopback HTTP endpoint, project-local tunnel client at `C:\Projects\.tools\openai-tunnel-client\tunnel-client.exe`, the active instance, and separate `operation` and `development` records.
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

The effect-specific dispatchers enforce the configured structured-result context budget. When an otherwise successful structured result exceeds that budget, KIS may return a bounded summary/preview plus an MCP `ResourceLink` to exact canonical JSON stored beneath the generated state root. Each successful offload receives an opaque random per-dispatch `kis-result:///...` grant; the stored envelope records the originating operation and an independent payload SHA-256, so identical results from separate dispatches never share read authority. Under the single-operator supervised trust model, possession of that unguessable returned grant is the bounded read authority for the one already-authorized result. Reads are size/integrity checked, do not replay the underlying operation, and do not mutate or delete state. Readability is bounded by the configured TTL and byte limit; active-store entry count is bounded, and expired entries are moved through the existing recoverable quarantine lifecycle during later store maintenance. If storage is unavailable, over-size, or at capacity, KIS preserves the explicit `RESULT_BUDGET_EXCEEDED` summary without claiming a resource. Resource retrieval does not change provenance, re-run eligibility/approval decisions, or create new Work authority.

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
- public `inspect_project` and bounded local-target `inspect_change` Discover operations for working-tree, staged, commit, range, and branch evidence;
- eleven registered Skills operations backed by the approved shared catalogue, including attributed outcome recording and bounded telemetry reporting, and enriched with capability-bearing runtime cards;
- normalized immutable Provider, Tool, Discover, Skill, Operation, Readiness, Exposure, Quality, and Workflow contracts;
- strict JSON-defined scoring weights, direct-profile limits, and Skills capability metadata;
- deterministic catalogue, readiness, eligibility, explainable scoring, workflow recommendation, and progressive exposure services;
- instance-scoped Provider and capability runtime state with no process-global latest-composition singleton;
- provider-neutral contracts, registry, health, explicit construction, and runtime composition;
- a provider-neutral persistent FastMCP client lifecycle with one outer connection per parent runtime and injectable provider startup bootstrap;
- pinned FastMCP `4.0.0b3` with the Tasks extension installed at gateway composition; selected multi-minute tools are optional MCP Tasks with synchronous fallback, explicit task IDs for same-server reconnect retrieval, request-scoped progress/cancellation, and KIS-owned execution deadline/stall handling that remains separate from the MCP task TTL;
- a strict central project registry with bounded `kis_list_projects` / `kis_project_status` catalogue operations and legacy repository-settings compatibility;
- a disposable repo-local recovery capsule beneath each registered project's own `.temp\\kis` directory, using the shared `EvidenceStore` for immutable worktree-isolated generations containing only typed identity fingerprints, central-generation hints, and hashed idempotency checkpoints; repository/Git/config/provider truth and `C:\\Projects\\.kis-mcp` remain authoritative, and missing/stale/corrupt capsule state is rebuilt rather than trusted;
- seven approval-gated exact registered-GitHub operations for immutable commit publication, tree-equivalent remote-default-rooted review-branch reconciliation, exact-head pull-request creation, merge-commit-only repository landing-policy configuration, canonical registered-Project schema commissioning with an optional manifest-bound field-only scope, exact-head pull-request merge, and exact-head non-default remote-branch deletion, exposed as discoverable virtual operations through `execute_external_action` with exact registered-target and remote-state verification;
- a bounded KIS speculative landing queue for centrally registered GitHub repositories, exposing read-only status plus approval-gated enqueue/reconcile/dequeue/land operations; queue entries freeze exact PR heads, candidate commits are cumulative two-parent merge commits, canonical verification runs on generation-scoped `kis-readonly-queue/main/**` refs, failed/conflicting/stale predecessors invalidate successors, and ALLGREEN landing reuses the existing exact-base registered publication primitive for fast-forward compare-and-swap base advancement;
- verified `kis-mcp` landing on `main`, through either exact pull-request merge or merge-queue land, emits one provider-neutral landed event to an injected KIS post-land dispatcher without changing the existing public landing result schemas; direct merge requires the provider-reported merge commit identity, while queue landing separately proves the commit that advanced the base; runtime composition injects the validated generated-state root into the dispatcher, and if exact landed identity is unavailable restart is skipped with bounded failure evidence without changing authoritative landing truth; a detached worker otherwise requires clean fast-forward synchronization of primary `main`, proves the required landed reference is contained, and launches only the `kis-dev` selected-instance lifecycle, retaining development-runtime evidence and never selecting `kis-op`;
- `execute_change_workflow` for two-axis verification/review execution using `small|medium|large` complexity plus additive objective risk triggers; verification selection and substantive KIS specialist reviews belong to implementation, are bound to the same inspected source fingerprint, and completed reviews must prove complete evidence for that exact source; `review_timeout_ms` bounds the aggregate specialist-review phase. Promotion/GitOps consumes the resulting review-closure evidence as an already-satisfied precondition and never initiates another KIS specialist review; repository-required human approval remains a provider/repository-policy gate rather than a second implementation review. `prepare_reviewable_pull_request` coordinates fixed verified-source-commit → exact-tree reconciliation → deterministic-metadata open-PR preparation, preserves both source and reconciled head SHAs, and intentionally stops before merge, remote-branch deletion, or worktree cleanup. The optional MCP Task `converge_change_to_done` resumes from a persisted PromotionReady handoff through one durable KIS-owned promotion checkpoint: registered default refresh, exact commit reconciliation, exact-head PR creation and provider-native Actions gating, Work merge readiness, exact-head merge, landed refresh, documentation reconciliation, Work completion, and governed cleanup. Completed stage observations persist across reconnect/restart, block replay, and remain handoff-fingerprint bound; MCP task identity is transport-only and does not replace Work/change/checkpoint authority;
- coordinator GitHub provenance admission that resolves claimed repository/issue/pull/head/merge identity through the live provider before work-packet issuance, freezes a tamper-evident verified tuple through worker handoff and reconciliation, rejects conflicting or stale tuples before integration, and requires provider-observed merge identity to match the delivered revision without rewriting the frozen exact head;
- GitHub MCP using one runtime-scoped client with one `get_me` bootstrap and explicit repository/Project authorization against all registered GitHub bindings, without mutable active-project authorization state;
- the existing Supabase provider implementation, OAuth/configuration, routing, and tests retained as parked code only; normal gateway composition does not register, mount, catalogue, recommend, report, or expose Supabase until a future operator-approved activation;
- Context7, Control Center, DBHub, Docker Hub MCP, GitHub MCP, and Serena adapters available under `context7_*`, `controlcenter_*`, `db_*`, `dockerhub_*`, `github_*`, and `serena_*` when enabled adapters build successfully; the checked-in runtime keeps Control Center disabled by default, while the retained Supabase runtime setting is deliberately ignored by normal composition; DBHub contributes stable project/binding read operations from one isolated child process per database binding, while Docker Hub remains an external registry connector separate from local Docker Engine/process operations;
- an NVIDIA NIM provider used only by the advisory code-review workflow;
- a generic Tools registry with a pinned Codex CLI `0.147.0` adapter, managed ChatGPT-authenticated home, exact-version/auth readiness, and a read-only mutation-detecting wrapper;
- `review_change_with_agent`, which accepts the same `working_tree|staged|commit|range|branch` source selector as local change inspection, projects deterministic source-bound evidence by review purpose, treats repository evidence as untrusted data, refuses incomplete or stale evidence, automatically routes each public review purpose through its qualified NVIDIA primary/backup models, streams provider deltas for liveness/telemetry, strictly validates output/tool contracts, runs safety/security through discovery → deterministic corroboration → cardinality-preserving Super/Ultra adjudication, and grants no mutation or nested-agent authority; explicit backend/model overrides remain direct compatibility/diagnostic paths rather than universal production fallback;
- provider-neutral Work Management with three Work-specific canonical machine contracts for item/vocabulary/applicability, lifecycle/operations, and selection semantics; typed records, command-plane settings, Python value sets, lifecycle guards, selector adapters, and the GitHub Project field projection are derived from or exact-validated against those authorities; `project_management_contract` exposes the normalized canonical contracts and fingerprints through the existing read-only MCP surface; configured provider-default intake aliases normalize only approved undeclared ingress states (currently GitHub Project `Todo` → command-plane `inbox`) without rewriting legitimate lifecycle states;
- a lifecycle-owned housekeeping runtime that activates only on `kis-op`, schedules unattended preview-only `work-management-reconciliation` and `backlog-readiness` runs through the parent authenticated provider session, persists bounded atomic receipts/failures/freshness beneath the KIS state root, and permits apply only from a fresh unchanged preview with a deterministic plan-derived idempotency key; Work Management no longer advertises a separate generic automation-switch surface, so scheduler authority is solely the explicit housekeeping runtime;
- a separate lifecycle-owned post-merge commissioning runtime whose observer schedules only on `kis-op`, discovers bounded merged-PR candidates through the authenticated GitHub provider, re-verifies provider `merged=true`, excludes every provider-native PR source-commit SHA from merge candidacy, resolves the exact default-branch merge commit only from the exact PR/head generated line plus GitHub `web-flow` committer identity and a sub-minute temporal sanity check against `merged_at`, proves complete changed-file enumeration against provider `changed_files`, then selects one exact landed schema-v4 change scope and binds its bytes to the exact merge-tree blob before accepting scope identity. The provider-native governed `change/<change-id>` head and the exact source Work card's canonical `Change ID` must independently corroborate that landed change; PR-body text is non-authoritative. Only immutable landed-governance scope defects are accounted as bounded `blocked_evidence` with no intake or projection mutation; provider/discovery/configuration/Work evidence uncertainty remains retryable and preserves the prior checkpoint. Valid candidates retain the existing live-surface classification, idempotent commissioning-issue creation, and canonical source live-verification projection; first activation establishes a current-time checkpoint with no historical backfill. The same runtime exposes read-only status/receipt/execution diagnostics plus an approval-required explicit runner that revalidates exact issue/merge/classifier/Work-claim identity, gates stale runtime generations without self-restart, executes one closed read-only probe profile, persists resumable per-attempt and aggregate evidence, and completes/blocks/leaves-open commissioning Work according to Passed/Blocked/Failed while source delivery remains independent. Successful commissioning closeout treats the GitHub issue-write response only as mutation acknowledgement, then requires an authoritative issue read-back for the exact issue number with `state=closed`; malformed, mismatched, or still-open read-back does not confirm terminal closure;
- a bounded GitHub Project adapter plus provider middleware that reads configured Projects, individual fields/items/status updates, adds existing issues or pull requests, permits bounded provider-native batch field updates, preflights revisions, deduplicates source records, and keeps Project/item deletion, Project creation, status-update creation, arbitrary schema administration, and unrestricted GraphQL outside the normal Work surface; the separate approval-gated registered-Project commissioner may create only manifest-declared fields/options/views for an exact central-registry Project binding and must re-read the canonical schema before reporting success;
- pre-merge `project_management_merge_readiness` gate evaluation that requires a passing provider-native GitHub Actions result for the exact pull-request head, plus post-merge `project_management_documentation_reconcile` orchestration using the existing `documentation_reconciliation_due` / `post_merge_complete` lifecycle; Work Management projects lifecycle state but is not authoritative for local change creation or Git landing facts;
- pinned AgentSys `6.0.1` and agnix `0.45.0` supervised bootstrap installers with isolated managed paths, staged validation, provenance evidence, and recoverable replacement; agnix is reacquired as the authoritative upstream Linux x86_64 release, checksum-verified and smoke-tested before promotion to `C:\Projects\.kis-mcp\tools\agnix\0.45.0`, then exposed through bounded `validate_agent_configuration` via WSL2 rather than the Smart App Control-blocked Windows helper; neither component is mounted as a general provider;
- the read-only KIS Control Center MCP App through the explicitly enabled `controlcenter_*` provider or the standalone process; the checked-in gateway composition keeps the UI provider disabled by default.

### Discover status

`inspect_project` returns deterministic local repository evidence for projects beneath `C:\Projects`. It applies JSON-configured retrieval limits, exclusions, text types, encodings, and budgets; rejects unsafe link, reparse, and configured hard-link cases structurally; reads local Git metadata through fixed bounded commands; parses Python with `ast`; discovers verification commands without executing them; and performs no network access or repository-code execution.

For registered projects with Discover memory enabled, the central Discover `EvidenceStore` generation remains reusable derived evidence under the canonical project/source `reconstructible-cache` namespace. The former Discover-specific namespace is compatibility-only: a legacy generation is migrated only when its full applicability fingerprint matches current project, source, Git, settings, and provider identity; mismatched, ambiguous, or corrupt legacy state is retained but never trusted. After that central generation is successfully created or reused, Discover publishes a small recovery hint to `<registered local_root>\.temp\kis` under a namespace derived from the active worktree. The hint records only fixed-schema identity fingerprints and the verified central generation ID. A local hint never makes an otherwise stale central generation current, and failure to read or write the local capsule degrades diagnostics only; it does not change Discover correctness.

The public local-evidence surface exposes `inspect_project`, bounded local-target `inspect_change` for working-tree, staged, commit, range, and branch evidence, `get_code_context`, and `analyze_change`; read-only `plan_change` composes that evidence as the Work-planning bridge. Context brokering may retain bounded support artifacts related to selected implementation evidence. Impact analysis includes direct and bounded transitive Python import dependants, bounded JavaScript/TypeScript dependency evidence, affected tests and verification handoffs, and advisory contract/documentation/configuration/policy relationships. `plan_change` reports planned paths, an evidence fingerprint, active-claim conflicts, and `REUSE`/`EXTEND`/`REPLACE`/`NEW` repository-pattern guidance; `analyze_change` may reconcile optional planned paths against actual scope and reports deleted/renamed replacement candidates only when remaining reference evidence exists. These outputs are Discover evidence and recommendations only: they do not implement Govern, authorize deletion, execute verification, or add a Work-policy decision.

### Provider and agent status

Normal Provider composition contains eight descriptors: Control Center, Desktop Commander, Context7 MCP, DBHub, Docker Hub MCP, GitHub MCP, NVIDIA NIM, and Serena MCP. The checked-in runtime JSON still retains a Supabase record as parked configuration, but normal composition suppresses it before provider status/capability projection; therefore Supabase does not appear as available, disabled, unregistered, misconfigured, or awaiting setup. Control Center remains disabled by default. DBHub uses the source-aware connector boundary and one isolated child process per registered binding; the exact pinned `v1.2.0` installation is commissioned, and the checked-in College `results` SQLite binding is live-verified for `search_objects` plus read-only `execute_sql`. Docker Hub remains separate from local Docker Engine operations and is commissioned at the exact approved source revision in credential-free public mode. Its KIS public surface exposes the six currently live-verified repository/tag read operations; upstream `search` remains intentionally hidden because the pinned provider's declared output schema rejects Docker Hub's current `search_after` response field. Successful DBHub/Docker Hub live commissioning persists exact-identity evidence beneath the configured KIS state root; a later runtime may report that historical live verification without claiming that its current child process has re-established upstream connection or tool discovery. Adapter build, invalid-result, mount, authentication, current-process readiness, and historical commissioning remain separate; one unavailable optional provider does not prevent Work, Discover, Skills, agent registration, or gateway startup.

GitHub construction owns one shared FastMCP `Client` for each parent KIS runtime. Before creating the fresh GitHub MCP child, KIS checks the configured GitHub CLI authentication state for `github.com`; when that CLI-managed credential is valid, KIS obtains it only in process memory and passes it only to the child through the provider's configured token environment variable. KIS does not persist or log the credential. If shared CLI authentication cannot be validated or resolved, the child starts token-free and retains the provider-native interactive OAuth fallback. The startup decision is reported only as redacted source/state/reason evidence. The provider lifecycle then connects once, performs one `get_me` bootstrap after connection, reuses that authenticated process across downstream sessions, and closes it only when that parent runtime stops. Restarting `kis-op` or `kis-dev` creates a new provider process and repeats the reuse-first authentication decision rather than inherently requiring another browser sign-in. Gateway composition loads one immutable central project registry and GitHub middleware authorizes explicit repository and Project coordinates against its registered union on every call.

Supabase is not part of normal runtime composition. Its existing provider lifecycle, OAuth, routing, settings, and tests are preserved for a future explicit activation, but no Supabase provider/capability/status/tool is exposed before that approval. NVIDIA is not mounted as a general passthrough. Codex CLI is a local executable Tool adapter, not a Provider-module connector.

`review_change_with_agent` accepts the same local Git source selector as `inspect_change`: `working_tree`, `staged`, `commit`, `range`, or `branch`, with the required target refs for non-working-tree sources. Discover remains the source-identity authority; the reviewer rechecks source currentness after external review before accepting a result. Evidence is projected deterministically by purpose (`changed-code-tests`, `security-boundary`, `architecture-boundary`, `hot-path`, `tests-and-behavior`, `docs-authority`, or `literal-contract`) and records included, omitted, and intentionally ignored paths. Repository instructions and changed code are explicitly treated as untrusted data in the external prompt. Incomplete evidence fails before invocation; stale evidence fails after invocation without surfacing findings.

With no explicit backend/model override, production review uses the qualified NVIDIA purpose matrix: code-quality Super→Ultra; safety-security Lightning→Ultra; architecture Ultra→Super; performance Super→Lightning; test-quality Super→Nano-text; documentation Lightning→Super; API/contracts Nano-Omni→Super. NVIDIA calls use SSE; provider reasoning/content/tool deltas are liveness heartbeats, with configured soft/hard stall thresholds and bounded telemetry. Rate pressure, capacity/degraded/unavailable states, transport failures, truncation, empty output, malformed JSON, contract-invalid output, and unexpected tool calls are typed and fail closed or move only to the route's qualified retry/backup. Strict output is exactly `summary`, `findings`, and `unknowns`. Safety/security additionally requires every discovered finding to survive deterministic path/evidence corroboration and complete candidate-cardinality adjudication by Super with Ultra fallback; partial adjudication is unusable.

`review_deadline_seconds` is one total budget across route attempts. Explicit `backend="codex-cli"` remains a direct compatibility/diagnostic path and never becomes an implicit production fallback. Explicit legacy NVIDIA aliases `nano`, `super`, and `ultra` remain direct compatibility overrides. `execute_change_workflow` still independently binds completed specialist-review evidence to verification's exact source fingerprint; #403 does not redefine whether a review is verification-grade evidence. `scripts/start-chatgpt.ps1` resolves `secret://provider/nvidia-nim/api-key` through the encrypted application vault and injects it only process-scoped as `NVIDIA_API_KEY`. Codex continues to use the pinned managed `CODEX_HOME`, read-only wrapper, mutation fingerprint guard, and exact authenticated version contract.

### Work-management status

The work-management domain remains provider-neutral and does not import FastMCP or GitHub layouts. It is an operational projection over authoritative local change records and Git/GitHub landing facts, not a prerequisite authority for creating a governed change. Three strict Work-specific JSON contracts own item/vocabulary/applicability semantics, lifecycle/operation semantics, and selection semantics; one normalized loader validates their structure, cross-references, runtime Python vocabularies, command-plane projection, and Project field projection. Both normalized-record and GitHub-Project next-work paths use the same canonical selection evaluator with adapter-specific evidence extraction/reason profiles, preserving the existing Priority → Effort → creation order → stable identity ranking and explicitly excluding the withdrawn #444 work-class tiers. Platform composition adds eight bounded task-level tools when strict work-management settings are enabled, while the existing read-only `project_management_contract` surface exposes canonical semantic sections and SHA-256 fingerprints without provider reads or mutation. The checked-in configuration manages `kis-mcp`, `chatgpt-skill`, `commodity`, `college`, and `import-isolate` through the shared user Project #1 backend. Feature, gate, and evidence modes plus backend bindings remain owned by work-management settings; generic `automation` switches are no longer advertised.

`settings/housekeeping.settings.json` separately binds unattended housekeeping to `kis-op`. Each enabled target declares an initial delay, recurring interval, project/repository identity, and bounded runner limits. Scheduler lifecycles reuse the already-authenticated parent GitHub/Work Management provider process, so restarting `kis-op` repeats the normal reuse-first GitHub authentication bootstrap before useful housekeeping can succeed. Scheduled execution is always preview-only. `kis_housekeeping_status` reports host activation, last attempt/success/failure, next due time, persisted receipt identity, age, and freshness; `kis_housekeeping_receipt` reads the corresponding bounded success/failure evidence. `kis_housekeeping_apply_receipt` is explicit supervised apply: it accepts only a fresh complete conflict-free preview, reruns preview against current authority, requires the actionable-plan fingerprint to remain identical, and derives the apply idempotency key from that fingerprint. Generated housekeeping evidence is atomic, retention-bounded, and stored beneath the configured KIS state root rather than repository authority.

`settings/post-merge-commissioning.settings.json` independently owns post-merge observer and live-surface execution policy. Its strict target/surface contract defines the `kis-op` host, polling/overlap/read/mutation bounds, ambiguous governed risk triggers, live-surface path/risk matchers, runtime refresh rule, closed `probe_id`, verification procedure, invariant, evidence target, and terminal success criterion. Candidate search is discovery only: each PR is re-read and must report `merged=true`; every provider-native PR source-commit SHA is enumerated and excluded from merge candidacy. The exact merge SHA must resolve uniquely from the registered default-branch commit stream using the exact PR/head generated line, GitHub `web-flow` committer identity, and a Git committer timestamp within less than one minute of provider `merged_at`; a one-minute-or-greater difference is inconsistent provider evidence. Provider `changed_files` must be positive and bounded, and exact merge-file pagination must enumerate exactly that distinct count before selecting one canonical `.work/changes/<change-id>/scope.json`. The observer resolves that path to the exact merge-tree blob, reads the scope at the exact merge SHA, verifies its Git blob identity, requires schema-v4 Work source identity, then independently corroborates the same change through the provider-native `change/<change-id>` PR head and the exact source Work card's canonical `Change ID`; PR-body text never gates admission or source identity. Only immutable landed-governance defects (`scope_path_missing`, `scope_path_ambiguous`, `scope_invalid`, `scope_identity_mismatch`) become bounded accounted `blocked_evidence` without commissioning intake or source-projection mutation. Provider, discovery, configuration, and Work evidence failures remain retryable, leave the run incomplete, and preserve the previous checkpoint. Valid evidence then follows the existing path: classify the exact merge, idempotently create/reuse one issue per `commission:<owner/repo>:<merge-sha>:<surface-id>`, and initialize only the canonical source live-verification fields as Pending, Not Required, or Blocked without touching source `Verification`. `kis_post_merge_commissioning_run` revalidates that generated issue, exact merge, classifier obligation, and active Work claim; for refresh/restart policy it requires the running runtime source to contain the merge and blocks without self-restarting when stale, then executes only the code-owned read-only probe selected by `probe_id`. Per-obligation execution state and immutable receipts are resumable/retryable under the existing commissioning state namespace; source state is recomputed across the complete obligation set using deterministic Failed > Blocked > Pending > Passed precedence and a singular or `set-<digest24>` Commissioning Key, with only a compact aggregate-receipt reference projected to the Project. Passed commissioning completes Work before closing its generated issue; Failed remains open/Active and Blocked transitions Work to Blocked. `kis_post_merge_commissioning_status`, `kis_post_merge_commissioning_receipt`, and `kis_post_merge_commissioning_execution` are read-only diagnostics on both instances; the runner is approval-required external work, while only `kis-op` schedules the observer. Initial activation establishes the current-time checkpoint and performs no historical backfill; #455 remains the explicit backfill owner.

`settings/work-management/github-project-schema.json` remains the repository-owned desired provider projection: **28 managed fields and 12 named views with executable semantics**. Its managed field names, provider types, and single-select options are exact-validated against `work-item-semantics.json`; the final three fields are `Live Verification`, `Commissioning Key`, and `Live Verification Evidence` for #419 commissioning evidence. `Verification` remains repository/source verification and cannot substitute for `Live Verification`, which is post-merge runtime proof. Each managed view declares its layout, filter, visible-field order, sort/group configuration, and board vertical grouping. The configured canonical manifest requires exactly 12 views, a non-empty current `Status` single-select, and exactly one `status:` qualifier per view containing only current canonical Status values; explicit alternate manifest files retain the generic parser contract. Legacy `Todo` / `In Progress` values may remain as unmanaged Project state but cannot be admitted by a canonical view filter. `Blocked By` remains text because queue admission distinguishes explicitly observed empty dependency evidence from unavailable evidence. `project_management_schema_status` compares official GitHub MCP field inventory plus the bounded registered-Project view inventory with that manifest deterministically; missing, malformed, incomplete, semantically mismatched, or behaviorally contradictory evidence keeps readiness false. Schema provisioning remains isolated to `kis_github_commission_registered_project_schema`; normal Work code does not directly mutate live schema, and arbitrary schema administration or delete/recreate paths remain outside the approved KIS surface.

Local review evidence is persisted only beneath `.work/reviews/<review-id>/` using bounded atomic replacement and conflict detection. Remote reconciliation defaults to preview and requires explicit apply plus an idempotency key. Safe create checks observed Project items for the same source issue or pull request before mutation, so restart does not duplicate records. Pre-merge readiness consumes exact PR/head evidence plus the Work projection and requires a passing provider-native GitHub Actions result with a concrete reference at the exact head; local verification may support development but does not satisfy the landing gate. After confirmed merge evidence, an operator or governing workflow may invoke `project_management_documentation_reconcile` to create/apply `documentation_reconciliation_due`; required documentation work remains in `Documentation` until a later invocation records `post_merge_complete` at an exact completion revision. Provider absence, unsupported methods, stale revisions, inaccessible state, incomplete pagination, and registry/work-management identity conflicts are corrective work-management outcomes rather than HR policy violations.

Current live commissioning status belongs to `docs/OPERATIONS.md`; dated evidence is retained in the applicable change/issue closeout records. Repository implementation now includes bounded schema/view commissioning rather than treating missing provider primitives as a permanent gap. Repository and Project authorization are validated through registered GitHub coordinates; historical repository-local routing settings remain compatibility data and do not widen those registered coordinates.

### Remote and standalone status

Both remote instance records contain distinct configured tunnel IDs and loopback ports. That configuration does not prove the Windows credential exists, a profile has been generated, the external tunnel is connected, ChatGPT has scanned the catalogue, or end-to-end operations have passed. External commissioning requires those separate supervised checks.

The KIS Control Center can run independently with `python -m kis_mcp.control_center` and is also mounted under `controlcenter_*` when enabled in provider-runtime settings. Both forms expose the same read-only evidence model. The mounted form receives the owning gateway instance's provider status explicitly; no process-global latest-composition state is used. Standalone rendering reports runtime mount state as unavailable rather than inferring zero mounted providers when no owning gateway status source is attached.

The remote runtime starts FastMCP with the checked-in `stateless_http=true` and JSON-response settings; startup and transport regression coverage keep the executable mode aligned with configuration. `kis_health` also returns a process-stable `server_instance_id`, `server_started_at`, source revision, contract fingerprint, selected runtime identity, and transport flags so two calls can be proven to target the same running process and public contract. Runtime observability retains only bounded correlation metadata for modern `server/discover`, `tools/list`, and `tools/call`, plus `initialize` solely when a dual-era legacy client uses it, together with existing tool-call key names and policy outcomes; it never retains prompt text, argument values, result bodies, client capabilities, or credentials. The Control Center exposes that bounded boundary evidence for supervised connection diagnosis.

None of these implementation-status statements restrict normal Work beyond HR-001, HR-002, and HR-003.
