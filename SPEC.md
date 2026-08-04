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

The repository does not contain an inherited SDK2 runtime, a custom replacement filesystem or terminal, a capability-profile permission framework, a governance subsystem, or a fork of Desktop Commander. It includes one bounded, read-only Discover foundation implemented natively under `src/kis_mcp/discover`; donor repositories remain source evidence only and are not runtime dependencies. Repository-local `.agents/skills` material remains procedural development guidance. The separate runtime Skills module resolves reusable procedures exclusively from the operator-approved shared root `C:\\Projects\\.agents\\skills` through `settings/skills.settings.json`, and its mutations re-enter the existing Work middleware and Desktop Commander backend.

## Product evolution

This specification defines the current implementation baseline. The approved final product direction is defined in `docs/PLATFORM-CONCEPT.md`.

The current FastMCP and Desktop Commander gateway is the initial Work-plane enforcement foundation of a larger three-plane platform:

```text
Discover → establish bounded repository evidence
Govern   → evaluate evidence against declared standards
Work     → perform controlled change under HR-001 / HR-002 / HR-003
```

The current Discover foundation provides bounded local repository discovery, deterministic evidence, local Git metadata, verification-command discovery without execution, and a pure Python structural index through one `inspect_project` tool. Future phases may add semantic providers, remote evidence, broader language intelligence, bounded context brokering, governance evaluation, reviews, audits, debugging, and workflow coordination. Those later capabilities remain targets, not current implementation claims.

The future platform model does not alter the closed Work enforcement decision set. Profiles, catalogues, governance findings, evidence requirements, readiness, or workflow selection must not become additional reasons to block an otherwise permitted invocation.

## Components

| Component | Responsibility |
|---|---|
| Desktop Commander | Provides ordinary filesystem, edit, search, process, testing, and local-development tools. |
| FastMCP gateway | Mirrors provider contracts, exposes gateway and Discover tools, evaluates concrete Work invocations, and forwards allowed provider calls. |
| Discover foundation | Performs bounded read-only local repository inspection through `inspect_project`, using JSON-configured evidence and output budgets. |
| Provider runtime | Explicitly registers approved providers, builds enabled GitHub and Supabase adapters, mounts successful FastMCP adapters under unique namespaces, contains adapter build/mount failures, and reports truthful runtime status. |
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

`settings.remote_mcp` defines exactly two local instances, `operation` and `development`, with separate ports, profile names, tunnel IDs, Windows Credential Manager target names, and explicit `configured` states. Selection is explicit through the launcher `-Instance` argument or the JSON `active_instance`; the runtime does not perform automatic failover.

Both instances expose the same standard mixed-purpose Desktop Commander and gateway tools. Transport, instance name, profile, catalogue metadata, approval metadata, or risk labels do not reduce the backend tool surface or create enforcement decisions. Only provider functionality whose every invocation is necessarily external-network-only may be omitted; the current pinned exceptions remain the feedback tool and `read_file.isUrl` mode.

The tunnel is an operator-supervised connector boundary outside ordinary Work invocations. It does not change the closed HR-001 / HR-002 / HR-003 decision set. Tunnel secrets are stored as per-user Generic Credentials in Windows Credential Manager. Checked-in JSON stores only a non-secret credential target name; setup and startup read the secret into a process-scoped environment variable used by the tunnel client and do not persist the value in repository files, generated profiles, or runtime state. Generated profiles and runtime diagnostics remain beneath `C:\Projects\.kis-mcp\tunnel-client`.

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
- `settings.discover` defines the enable flag, exclusions, text types, encodings, hard-link behavior, and all file, directory, byte, depth, time, Git, Python-index, evidence, and output budgets.
- `settings/providers/platform-runtime.provider.json` selects exactly the approved external provider IDs, records runtime enablement, and assigns unique lower-case namespaces. It contains no credentials.
- `settings.remote_mcp` defines the loopback HTTP endpoint, `C:\Tools\openai-tunnel-client\tunnel-client.exe`, the active instance, and separate `operation` and `development` records.
- Each remote instance stores its port, profile name, explicit `configured` state, non-secret `tunnel_id`, and non-secret `tunnel_credential_target` used to retrieve its per-user Generic Credential from Windows Credential Manager.
- `policy/kis-mcp.policy.json` contains exactly HR-001, HR-002, and HR-003.

A remote instance may have a blank tunnel ID only while `configured` is `false`. Before profile setup or startup, the operator supplies the real tunnel ID, changes `configured` to `true`, and stores the secret once with `scripts\set-tunnel-credential.ps1`. Profile setup and startup fail closed when the instance is unconfigured or the named Windows credential is missing. API keys, credential values, tunnel profile YAML, and generated runtime state are never committed.

Configuration and implementation-status fields do not disable otherwise permitted Desktop Commander tools or create another policy decision.

## Skills module

The implemented Skills module resolves one reusable procedure catalogue from `C:\Projects\.agents\skills`. It builds a deterministic immutable snapshot after validating `SKILL.md` frontmatter, file paths, configured suffixes, encodings, links, sizes, and limits. Repository-local `.agents/skills` is not part of this runtime catalogue.

The module exposes bounded list, search, load, file-search, file-read, refresh, and structural-evaluation operations. ChatGPT loads the returned instructions and executes their workflows through ordinary kis-mcp Work tools; the server does not import or automatically execute arbitrary skill code.

Skill creation validates a complete proposed entrypoint, stages it beneath `C:\Projects\.kis-mcp\temp\skills`, and publishes it with Desktop Commander `create_directory`, `write_file`, and `move_file`. Skill improvement requires the active file SHA-256 and uses Desktop Commander `edit_block` with one exact expected replacement. Every mutation calls `FastMCP.call_tool(..., run_middleware=True)`, so the existing three-rule middleware evaluates the concrete Work effects.

`settings/skills.settings.json` and `contracts/skills/settings.schema.json` define the exact roots, limits, supported suffixes, and traversal controls. Initial catalogue failure does not prevent ordinary Work/gateway startup; Skills calls return a corrective `SKILLS_*` error until the source is repaired and the server is restarted. `SKILLS_*` failures are structural or application errors and do not expand the closed Work policy decision set.

## Public interface

Expose Desktop Commander's normal non-network-only tool surface, approved namespaced provider tools, five gateway operations, one Discover operation, and nine Skills operations:

- `kis_health` — report Desktop Commander availability, policy fingerprint, and configured roots;
- `kis_provider_status` — report provider registration, runtime enablement, build and mount results, provider-neutral readiness, and explicitly unverified commissioning states;
- `kis_quarantine_path` — move one eligible path into recoverable quarantine;
- `kis_list_quarantine` — list bounded recoverable operations;
- `kis_restore_quarantine` — restore one intact item without overwrite;
- `inspect_project` — return bounded deterministic local repository evidence without executing repository code, tests, builds, or discovered verification commands;
- `list_skills`, `search_skills`, and `load_skill` — discover and load reusable procedures;
- `search_skill_files` and `read_skill_file` — inspect bounded supporting files;
- `refresh_skills` and `evaluate_skill` — rebuild or evaluate the immutable catalogue snapshot;
- `create_skill` and `improve_skill` — validate and mutate shared skills through the Work backend;
- `github_*` and `supabase_*` — namespaced upstream provider tools only when the corresponding adapter builds and mounts successfully.

Provider catalogue membership or mount success does not prove authentication, upstream connectivity, tool discovery, or live verification.

Do not add capability-profile permission systems, tiers, approvals, or broad replacement wrapper surfaces. Discover and Skills are approved versioned module contracts and do not alter Work authorization.

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
- Discover schemas and settings, canonical identity, unsafe links and hard links, bounded traversal and reads, deterministic detection, fixed local Git evidence, pure Python AST indexing, evidence integrity, exact output compaction, donor independence, plane boundaries, and additive tool registration.

Verification must run through the locked external project interpreter, not a globally resolved executable, and must keep caches and generated state beneath `C:\Projects\.kis-mcp`. Verification demonstrates detection quality; it does not create a permission gate for tools outside the three prohibited intents.

## Current implementation boundary
The current implementation includes repository authority, JSON configuration, the closed three-rule policy core, the Desktop Commander Work adapter, quarantine support, local stdio startup, settings-driven streamable HTTP startup for separate `operation` and `development` instances, Windows Credential Manager-backed tunnel credential retrieval, the bounded Discover foundation, the shared Skills catalogue with Work-backed create/improve operations, and provider runtime composition.

`inspect_project` is registered on the same gateway and returns deterministic local repository evidence for projects beneath `C:\\Projects`. It applies only JSON-configured retrieval limits, exclusions, text types, encodings, and budgets; rejects unsafe link/reparse and configured hard-link cases structurally; reads local Git metadata through fixed bounded commands; parses Python with `ast`; discovers verification commands without executing them; and performs no network requests or repository-code execution.

The verified Skills merge established an additive Work/gateway/Discover/Skills catalogue and preserved fail-open Skills registration. The Provider registry contains Desktop Commander, GitHub MCP, and Supabase descriptors. `build_server()` selects the approved external GitHub and Supabase providers from strict JSON runtime settings, builds enabled adapters in deterministic order, mounts successful FastMCP adapters under `github_*` and `supabase_*`, and contains unavailable or invalid adapters without preventing Work, Discover, Skills, or gateway startup. `kis_provider_status` reports registration, readiness, build, mount, and explicitly unverified commissioning states. Successfully mounted upstream tools extend the core catalogue dynamically and do not alter the three-rule Work policy.

This slice does not commission GitHub or Supabase authentication. The GitHub official binary, interactive OAuth/device flow, authenticated private-repository read, Supabase hosted OAuth/DCR, token persistence, project-scoped read, upstream tool discovery, and main ChatGPT endpoint live verification remain dedicated follow-up work.

The external Secure MCP Tunnel and ChatGPT app hop are not claimed as commissioned until the operator supplies the real `tunnel_id` and control-plane scope association for each instance, marks it configured, creates the profiles, and completes the live ChatGPT tool scan. These implementation-status statements do not restrict normal tools beyond HR-001, HR-002, and HR-003.
