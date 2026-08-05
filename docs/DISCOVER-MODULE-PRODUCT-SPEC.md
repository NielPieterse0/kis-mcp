# kis-mcp Discover Module Product Specification

## Document status

| Field | Value |
|---|---|
| Product | `kis-mcp` Platform |
| Module | Discover |
| Repository | `C:\Projects\kis-mcp` |
| Canonical remote | `https://github.com/NielPieterse0/kis-mcp.git` |
| Status | Approved; bounded local Discover v1 runtime complete; optional provider expansion remains staged |
| Date | 2026-08-05 |
| Parent platform concept | [`PLATFORM-CONCEPT.md`](PLATFORM-CONCEPT.md) |

This specification defines the complete product boundary, target architecture, workflows, evidence contracts, provider-harvesting model, testing relationship, security posture, migration strategy, delivery roadmap, and acceptance criteria for the Discover plane of `kis-mcp`.

The key words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** are normative.

Runtime capability is established only by checked-in contracts, settings, tool registration, and fresh tests. As of 2026-08-05, the bounded local Discover v1 runtime exposes exactly `inspect_project`, `inspect_change`, and `get_code_context` through the existing kis-mcp composition seams. Provider-admission evidence and explicit project-catalog services are implemented as internal foundations and are not additional public tools.

Optional semantic-provider, remote-forge, registry, background-index, and process-backed analyzer capabilities remain staged. Their absence must produce bounded degraded evidence or explicit unknowns; it does not make the deterministic local Discover v1 runtime unavailable.

## 1. Executive summary

Discover is the evidence and context plane of the `kis-mcp` Platform.

It answers five questions:

1. What is this repository?
2. What code, interfaces, dependencies, tests, instructions, contracts, and controls does it contain?
3. What changed, and what is likely affected?
4. Which evidence, tools, providers, and checks are relevant to the current task?
5. What remains unknown, unverified, missing, stale, or risky?

Discover is not an execution engine, Work policy authority, installer, repair agent, or general-purpose command runner.

```text
Discover  -> establishes bounded evidence and recommendations
Govern    -> evaluates evidence against declared standards
Work      -> executes approved checks and controlled changes
```

The target implementation consolidates and adapts:

- the mature `sdk-tool` modular analysis, read-authority, project-intelligence, contract, catalogue, and registration foundations;
- the hardened `dev-intel-tool` `inspect_project`, repository scanner, detector, Git, confidence, unknown-state, and output-budget behavior;
- selected read-only filesystem and Git hardening from `mcp-tool`;
- the existing `kis-mcp` identity, configuration, contracts, FastMCP composition, three-rule Work enforcement, and recoverable quarantine;
- future approved semantic, forge, API-contract, testing, security, and documentation providers.

The result is a small public Discover surface backed by a modular provider registry, normalized evidence model, bounded repository and code atlases, change-impact analysis, verification intelligence, and a task-scoped context broker.

## 2. Position within the kis-mcp Platform

The platform contains three bounded planes in one runtime:

```text
kis-mcp Platform
├── Discover
├── Govern
└── Work
```

Discover owns no mutation authority. Govern owns no ordinary repository mutation authority. Work remains the only plane that executes approved checks or changes repositories.

### 2.1 Shared kernel dependencies

Discover consumes these shared platform services:

- `ProjectIdentity`;
- `ReadAuthority`;
- `EvidenceStore`;
- `ResultBudgeter`;
- `ProviderRegistry`;
- `ToolCatalogue`;
- `WorkflowCoordinator`;
- `VerificationRegistry`.

Discover MUST NOT create competing project identity, read authorization, evidence identity, provider lifecycle, or output-budget implementations.

The Work `PolicyEngine` continues to enforce exactly HR-001, HR-002, and HR-003. Discover read boundaries, exclusions, parser failures, and budget failures are structural retrieval decisions. They MUST NOT create a fourth Work prohibition.

### 2.2 Stable responsibility model

| Capability | Discover | Govern | Work |
|---|---|---|---|
| Resolve repository identity | Owns evidence | Verifies declared authority | Uses resolved target |
| Read repository files | Owns bounded reads | Defines repository standards | Reads when required for approved work |
| Parse source and manifests | Owns pure parsing | Evaluates compliance | Uses findings for changes |
| Build file, module, symbol, and relationship maps | Owns | May require coverage | Consumes |
| Inspect local Git state | Owns fixed read templates | Defines branch and change rules | Owns Git mutation |
| Read forge evidence | Owns normalized read evidence | Evaluates controls | Owns remote mutation |
| Discover tests and checks | Owns inventory and impact mapping | Defines required gates | Executes checks |
| Run tests, builds, linters, browsers, or package managers | Prohibited | Prohibited | Owns execution |
| Discover providers | Owns candidate discovery and evidence | Approves admission | Installs and validates approved candidates |
| Produce task context | Owns | Adds applicable rules | Consumes |
| Modify repositories | Prohibited | Prohibited except controlled governance workflows | Owns authorized mutation |

### 2.3 Testing is cross-plane

```text
Discover
  - inventory frameworks, files, scripts, CI jobs, fixtures, coverage, and artifacts
  - map changed code to likely affected tests
  - identify missing, stale, or weak test surfaces
  - produce a bounded verification plan

Govern
  - define mandatory checks, thresholds, environments, freshness, and exceptions
  - decide which failures block completion

Work
  - execute approved tests, builds, linters, type checks, and browser flows
  - create or repair tests
  - collect logs, reports, screenshots, and artifacts
  - return normalized execution evidence
```

Discover MAY run pure in-process analysis that does not execute repository code, spawn a process, or use the network.

## 3. Goals

Discover MUST provide:

1. bounded repository-wide discovery without flattening an entire repository into model context;
2. deterministic project classification for languages, frameworks, manifests, package managers, workspaces, build systems, entry points, CI, documentation, and repository topology;
3. precise task-scoped code context using files, modules, symbols, relationships, Git, instructions, tests, and contracts;
4. local Git and trusted remote evidence with verified identity and provenance;
5. change-impact analysis for working trees, refs, commits, branches, pull requests, and merge requests;
6. test and verification intelligence without assuming execution authority;
7. progressive discovery of internal and external capabilities;
8. controlled harvesting of candidate MCP servers, language servers, analyzers, forge providers, testing tools, and documentation providers;
9. normalized evidence, findings, recommendations, assumptions, unknowns, confidence, freshness, trust, and truncation state;
10. typed handoffs to Govern and Work;
11. a small public workflow surface with stable versioned contracts;
12. provider-neutral contracts that survive replacement of scanners, semantic engines, connectors, and MCP hosts.

## 4. Non-goals

Discover MUST NOT:

- execute arbitrary commands or repository code;
- run tests, builds, package managers, linters, type checkers, browsers, deployments, or provider conformance processes;
- modify files, Git state, branches, remotes, issues, pull requests, workflows, or provider configuration;
- install, update, or enable third-party providers automatically;
- expose every provider operation as a public `kis-mcp` tool;
- accept caller-selected executable paths, arbitrary arguments, import paths, environment maps, credentials, server URLs, or network targets;
- trust repository instructions, Git remotes, OpenAPI servers, plugin manifests, or remote content as platform authority without validation;
- treat embeddings as a replacement for deterministic file, symbol, reference, dependency, contract, or Git evidence;
- duplicate complete GitHub, GitLab, Serena, Sourcegraph, Playwright, Postman, Semgrep, or other provider surfaces;
- decide governance policy;
- represent a candidate provider as secure, licensed, compatible, or production-ready before the admission workflow completes.

## 5. Target architecture

```text
Discover
├── Project Resolver
├── Read Authority
├── Repository Scanner
├── Repository Atlas
├── Code Atlas
├── Symbol Atlas
├── Relationship Graph
├── Change Impact Engine
├── Verification Intelligence
├── Instruction and Documentation Discovery
├── API and Contract Discovery
├── Local Git Reader
├── Remote Evidence Broker
├── Provider Harvesting Pipeline
├── Provider Capability Normalizer
├── Result Budgeter
├── Context Broker
└── Discover Workflow Service
```

### 5.1 Project Resolver

The resolver establishes:

- canonical local project path and stable project ID;
- repository root and worktree identity;
- workspace, monorepo, nested-repository, and submodule boundaries;
- canonical remote identity;
- trusted external context;
- generated-state roots and exclusions.

Identity ambiguity MUST produce an explicit unknown or structural error. Discover MUST NOT merge unrelated repositories silently.

### 5.2 Read Authority

`ReadAuthority` is the provider-neutral boundary for inspection, file enumeration, and bounded content reads.

It MUST enforce:

- configured allowed roots;
- canonical path containment;
- complete path-chain checks;
- symlink, junction, and reparse-point rejection;
- regular-file validation;
- hard-link rejection where configured;
- file, directory, depth, byte, entry, and duration limits;
- deterministic labels and ordering;
- read-time identity and size revalidation;
- explicit omission and truncation reporting.

Read controls are retrieval and exposure rules. They are not HR-001, HR-002, or HR-003 decisions.

### 5.3 Repository Scanner

The scanner identifies:

- languages and file types;
- manifests, locks, package managers, frameworks, SDKs, and build systems;
- workspaces, modules, applications, services, libraries, tests, infrastructure, and documentation;
- entry points and public surfaces;
- generated, vendored, cache, build, coverage, and state paths;
- CI and automation configuration;
- test configuration and test files;
- instructions, governance artifacts, schemas, API contracts, and deployment artifacts;
- protected or likely secret-bearing files without returning secret values.

Traversal and content reading remain separate operations through `ReadAuthority`.

### 5.4 Repository Atlas

The Repository Atlas records structural repository evidence:

- projects, workspaces, packages, modules, services, applications, libraries, infrastructure, tests, documentation, and generated assets;
- instruction and ownership scopes;
- manifest and dependency roots;
- build and verification entry points;
- CI and deployment surfaces;
- repository and governance topology.

The atlas MUST distinguish observed structure from inferred intent.

### 5.5 Code Atlas

The Code Atlas maps:

- source files and modules;
- imports and exports;
- package and module dependencies;
- public and internal entry points;
- central and high-fan-in modules;
- test-to-source relationships;
- generated and vendored code;
- configuration and schema consumers;
- instruction and ownership scope.

Pure standard-library parsers MAY contribute deterministic structural evidence. Python AST analysis developed in `sdk-tool` is the initial reference implementation.

### 5.6 Symbol Atlas

The Symbol Atlas normalizes semantic evidence from pure parsers, language servers, indexes, or approved providers.

It MAY include:

- classes, functions, methods, constructors, constants, types, interfaces, traits, modules, namespaces, endpoints, commands, jobs, and tests;
- signatures and locations;
- declarations, definitions, implementations, references, callers, callees, inheritance, imports, exports, overrides, and diagnostics;
- provider confidence, freshness, and capability limitations.

Serena is the preferred first read-only semantic-provider candidate. The public contract MUST remain provider-neutral.

### 5.7 Relationship Graph

The graph combines repository and code evidence:

```text
file -> module -> symbol -> dependency -> test -> check -> workflow -> artifact
```

Each edge MUST declare its relationship type, source evidence, confidence, and whether it is observed, parser-confirmed, provider-confirmed, conventional, or heuristic.

### 5.8 Change Impact Engine

The engine accepts a working-tree diff, staged diff, ref range, commit range, branch comparison, pull request, or merge request.

It identifies:

- changed files, modules, symbols, contracts, schemas, manifests, policies, docs, and tests;
- direct and bounded transitive dependants;
- public-interface changes;
- affected verification and likely missing tests;
- documentation and governance impact;
- CI, review, and remote-check evidence;
- risks and unresolved unknowns.

Observed changes, deterministic relationships, heuristic impact, and unavailable evidence MUST remain distinct.

### 5.9 Verification Intelligence

Verification Intelligence discovers and normalizes verification without executing it.

It inventories:

- repository scripts and fixed command identities;
- unit, integration, contract, component, end-to-end, browser, database, migration, security, performance, and smoke tests;
- lint, type-check, format, build, schema, documentation, policy, packaging, and installation checks;
- coverage declarations and reports;
- CI jobs, matrices, required checks, artifacts, branch protections, prerequisites, and environments.

Each item MUST use one provenance state:

- `declared`;
- `conventional`;
- `recommended`;
- `remote_observed`;
- `governance_required`.

Discovered command text is evidence only. A Work handoff MUST reference an approved operation or registered workflow identity.

### 5.10 Instruction and Documentation Discovery

Discover locates and classifies:

- `AGENTS.md`, scoped agent instructions, contribution guidance, and coding standards;
- README, architecture, ADR, API, operations, security, deployment, testing, and governance documents;
- generated documentation and its authoritative source;
- documentation build and drift checks.

Discover records location, scope, references, apparent authority, duplication, and freshness evidence. Govern decides correctness and authority.

### 5.11 API and Contract Discovery

Discover identifies:

- OpenAPI and Swagger specifications;
- AsyncAPI descriptions;
- GraphQL schemas and persisted operations;
- Protocol Buffers and gRPC definitions;
- JSON Schema;
- database schemas, migrations, policies, and generated types;
- MCP tool, resource, prompt, manifest, and capability schemas.

Discover MUST NOT contact server URLs found in specifications. It MAY classify likely effects but MUST label uncertainty.

### 5.12 Local Git Reader

Local Git evidence MUST use fixed read-only argument templates, direct argument arrays, bounded output, disabled prompts, disabled paging, disabled external diff and text conversion, isolated configuration, and one bounded deadline.

Supported evidence SHOULD include:

- repository root and worktree metadata;
- branch and detached-head state;
- status and changed paths;
- staged and unstaged diffs;
- commits, logs, merge bases, tags, and ref comparisons;
- tracked files, submodules, and worktrees;
- sanitized remotes.

Git inspection MUST NOT trigger hooks, filters, credential helpers, remote access, index mutation, ref mutation, or worktree mutation.

### 5.13 Remote Evidence Broker

The broker normalizes read evidence from approved connectors and fixed provider adapters.

Initial provider targets are GitHub and GitLab. Evidence MAY include repository metadata, pull or merge requests, changed files, commits, reviews, threads, checks, workflows, pipelines, jobs, logs, artifacts, protections, releases, and authorized security findings.

Remote evidence MUST match the canonical local repository identity before it is merged. A mismatch remains untrusted and generates a corrective request.

### 5.14 Provider Harvesting Pipeline

The pipeline discovers, deduplicates, evaluates, and proposes provider candidates. It does not install or enable them.

```text
source discovery
  -> canonical identity and deduplication
  -> provenance, version, revision, and license evidence
  -> capability and effect extraction
  -> static contract and security inspection
  -> compatibility and overlap assessment
  -> proposed Work conformance plan
  -> Govern admission decision
  -> approved provider manifest and lock
```

### 5.15 Context Broker

The Context Broker returns the smallest sufficient evidence bundle for one task.

It combines project identity, files, modules, symbols, relationships, Git, instructions, tests, contracts, providers, findings, unknowns, confidence, and truncation under explicit budgets.

It MUST NOT return a repository dump.

## 6. Public workflows

The Discover v1 public surface is deliberately fixed and small:

- `inspect_project`;
- `inspect_change`;
- `get_code_context`.

Provider-admission evidence, explicit project cataloging, and future catalogue operations remain internal service capabilities unless a later approved contract explicitly changes the public surface. Inactive provider operations are not registered.

### 6.1 `inspect_project`

`inspect_project` returns bounded repository-wide intelligence.

Required top-level response fields:

```json
{
  "schema_version": 1,
  "tool": "inspect_project",
  "project": {},
  "repository_atlas": {},
  "code_atlas": {},
  "verification": {},
  "contracts": {},
  "instructions": [],
  "git": {},
  "remote": {},
  "providers": {},
  "evidence": [],
  "findings": [],
  "recommendations": [],
  "handoffs": [],
  "assumptions": [],
  "unknowns": [],
  "confidence": "high",
  "truncated": false,
  "truncation_reasons": []
}
```

The schema MAY allow empty sections but MUST preserve stable field identity and versioning.

The first implementation phase covers deterministic local identity, topology, manifests, languages, package managers, workspaces, entry points, instructions, documentation, verification declarations, local Git summary, evidence, confidence, unknowns, and truncation. Pure Python structural indexing MAY populate a bounded Code Atlas.

### 6.2 `inspect_change`

Supported targets SHOULD include current working tree, staged changes, commits, commit ranges, branch comparisons, pull requests, and merge requests.

The response MUST include:

- change identity and source;
- changed files and symbols;
- affected modules and dependants;
- public contract and schema changes;
- likely affected tests and required verification;
- documentation, configuration, policy, and governance impact;
- remote review and CI evidence when available;
- risks, unknowns, confidence, and Work handoffs.

### 6.3 `get_code_context`

The request identifies a project, task, and explicit budget.

```json
{
  "project": "kis-mcp",
  "task": "Add GitLab merge-request evidence to inspect_change",
  "budget": {
    "max_chars": 24000,
    "max_files": 10,
    "max_symbols": 40,
    "max_relationships": 80
  }
}
```

The response contains relevant modules, symbols, files, relationships, instructions, tests, contracts, provider dependencies, unknowns, provenance, and truncation. It MUST NOT flatten the repository.

## 7. Evidence and result contracts

### 7.1 Evidence item

```json
{
  "id": "ev-...",
  "kind": "file|symbol|git|remote|manifest|test|contract|provider|diagnostic",
  "subject": "stable subject identity",
  "source": {},
  "location": {},
  "observed_at": "optional temporal field",
  "revision": "optional immutable revision",
  "trust": "trusted|untrusted|partial|unknown",
  "confidence": "high|medium|low",
  "freshness": "current|stale|unknown",
  "summary": "bounded evidence summary",
  "details": {},
  "truncated": false
}
```

Evidence IDs MUST be unique in one response. Every retained finding, relationship, recommendation, and handoff reference MUST resolve.

### 7.2 Finding

A finding records an observed issue or risk. It MUST include stable code, title, severity, scope, observation, impact, evidence IDs, confidence, remediation or next evidence, and owning plane.

### 7.3 Recommendation

A recommendation proposes a next action without claiming authority. It MUST include ID, category, action, rationale, evidence IDs, benefit, cost class, risks, owning plane, and optional workflow or provider candidate.

### 7.4 Unknown

Unknowns are first-class outputs. They SHOULD identify missing local evidence, missing connector evidence, unavailable capability, budget omission, parse failure, identity mismatch, stale result, unsupported language or format, and unresolved heuristics.

### 7.5 Handoff

```json
{
  "handoff_id": "ho-...",
  "target_plane": "govern|work",
  "workflow": "evaluate_rule|run_verification|evaluate_provider|propose_change",
  "reason": "...",
  "inputs": {},
  "evidence_ids": [],
  "required_authority": [],
  "expected_result_contract": "..."
}
```

### 7.6 Determinism

For identical repository state, configuration, provider versions, remote evidence, and budgets, substantive ordering and classifications SHOULD be deterministic. Time-sensitive metadata MUST NOT destabilize the deterministic evidence payload.

### 7.7 Output budgeting

Budgets MUST apply to traversal entries, files, directories, bytes, symbols, relationships, Git history, diff size, remote items, logs, findings, recommendations, candidates, duration, and serialized output.

Compaction MUST preserve:

1. the stable top-level contract;
2. project and request identity;
3. material findings;
4. evidence referenced by retained findings and handoffs;
5. unknowns and truncation reasons;
6. confidence and trust state.

If the minimum valid contract cannot fit, the operation MUST fail explicitly.

## 8. Testing and verification contract

### 8.1 Discovery responsibilities

Discover detects verification from repository evidence for supported ecosystems, including Python, JavaScript and TypeScript, .NET, Java and Kotlin, Go, Rust, C and C++, databases, APIs, web applications, and repository governance.

### 8.2 Verification graph

```text
change
  -> affected component
  -> applicable risk
  -> candidate test or check
  -> declared operation identity
  -> required environment
  -> expected evidence or artifact
  -> governing rule
```

### 8.3 Missing-test and weak-surface recommendations

Discover MAY recommend testing when evidence supports a gap. Absence of evidence MUST remain distinct from proof of absence.

### 8.4 Work handoff

A verification handoff MUST contain stable verification ID, provenance, rationale, evidence IDs, registered operation or workflow identity, project-relative working directory, prerequisites, expected effects, expected outputs, timeout class, governing requirement, and requirement level.

It MUST NOT contain an unvalidated executable path or arbitrary caller-controlled command.

### 8.5 Returned execution evidence

Work returns normalized command or workflow identity, timestamps, exit state, bounded logs, diagnostics, test counts, quality metrics, artifacts, non-secret environment fingerprint, freshness, and provenance. Discover MAY incorporate that evidence into refreshed results.

## 9. Provider and source harvesting

### 9.1 Donor priority

1. `sdk-tool` is the primary architecture and implementation donor.
2. `dev-intel-tool` supplies repository-inspection parity and hardening.
3. `mcp-tool` supplies selected traversal, Git, diagnostics, and operation-shape hardening.
4. Other repositories and external ecosystems supply candidate patterns only.

No donor becomes a runtime dependency.

### 9.2 sdk-tool consolidation

Retain and adapt:

- portable immutable analysis contracts;
- provider-neutral `ReadAuthority`;
- settings, authorization, readiness, and exposure separation;
- language, analyzer, workflow, and capability registries;
- coordinator-owned normalization, limits, errors, partial results, and next actions;
- pure Python AST adapter;
- project workflow discovery with `discovered_only` authority;
- bounded Python project indexing;
- thin backend-neutral tool binders;
- contract, schema, backend-parity, architecture, and transport tests;
- progressive capability discovery and Serena provider strategy.

Do not import sdk-tool policy decisions, execution-worker design, separate product identity, backend host duplication, or compatibility catalogue wholesale.

### 9.3 dev-intel-tool consolidation

Adapt:

- `inspect_project` product contract;
- repository topology, manifests, frameworks, workspaces, entry points, CI, package managers, modules, instructions, and verification detectors;
- evidence-linked findings and recommendations;
- confidence, assumptions, unknowns, connector requests, and truncation;
- hardened scanner and read-time revalidation;
- fixed-template local Git summary and remote redaction;
- deterministic output compaction;
- schema snapshots and isolated-install verification.

Standalone retirement is a later migration decision after parity and consumer migration.

### 9.4 mcp-tool consolidation

Adapt only read-side patterns that strengthen Discover:

- streaming traversal with visited-entry, byte, and deadline limits;
- path and reparse validation;
- Git repository and worktree metadata validation;
- isolated Git configuration;
- disabled external diff and text conversion;
- bounded stdout and stderr;
- structured corrective diagnostics;
- dedicated-operation preference and effect metadata.

Mutation, GitHub mutation, command execution, downloads, browser execution, database mutation, and worktree management remain Work capabilities.

### 9.5 Other local sources

Discover MAY harvest architectural patterns and metadata from `work-tool`, GPT-OS, `doc-solution`, and approved local plugin corpora. These sources remain evidence and candidate indexes, not automatic authority.

### 9.6 Candidate descriptor

Each provider candidate MUST normalize canonical source, type, version or revision, artifact digest where available, license, maintainer, capabilities, languages, effects, authentication, network posture, installation, schemas, health, conformance, overlap, risks, evidence IDs, and trust state.

### 9.7 Admission

Discover produces evidence and proposed plans. Govern decides rejection, quarantine, experimental admission, optional approval, preferred status, deprecation, or removal. Work performs cloning, building, installation, startup, smoke testing, and conformance execution.

## 10. Git and forge integration

### 10.1 Local Git

Local Git is deterministic read evidence and is included in the initial implementation roadmap.

### 10.2 GitHub

Initial strategy: normalize evidence from approved connectors, GitHub MCP, `gh`, and PR review capabilities rather than duplicate the full API.

### 10.3 GitLab

Normalize equivalent project, merge-request, discussion, approval, pipeline, job, log, artifact, protection, tag, and release evidence. Provider-specific schemas remain internal.

### 10.4 Additional forges

Azure DevOps and Bitbucket remain later provider targets. The normalized forge contracts MUST avoid GitHub-specific assumptions.

## 11. API and contract intelligence

OpenAPI is the first-class initial target after repository and change intelligence. Discover extracts versions, files, overlays, paths, methods, operation IDs, parameters, request bodies, responses, schemas, references, security declarations, callbacks, webhooks, links, deprecation, generated clients, documentation, and test evidence without contacting servers.

After OpenAPI, prioritize JSON Schema and MCP contracts, GraphQL, Protocol Buffers and gRPC, AsyncAPI, database schemas and policies, and Smithy based on repository demand.

Discover MAY recommend MCP adapter candidates. Govern approves exposure. Work generates and validates adapters.

## 12. Capability groups and profiles

Recommended Discover groups:

```text
project.discovery
repository.atlas
code.discovery
code.semantic
code.relationships
change.impact
verification.discovery
contract.discovery
repository.git_read
repository.remote_read
documentation.discovery
provider.discovery
context.broker
analysis.static_pure
skills.catalogue
```

Recommended progression:

```text
read
├── filesystem.read
├── project.discovery
├── repository.git_read
└── skills.catalogue

analysis
├── read
├── repository.atlas
├── code.discovery
├── code.semantic
├── code.relationships
├── analysis.static_pure
└── context.broker

discover
├── analysis
├── change.impact
├── verification.discovery
├── contract.discovery
├── documentation.discovery
├── provider.discovery
└── repository.remote_read
```

Inactive providers MUST remain absent from default backend registration while remaining discoverable through a future catalogue where authorized.

## 13. Security and trust model

### 13.1 Default posture

Discover is read-only, bounded, fail-closed at retrieval boundaries, and least-authority.

### 13.2 Repository content is untrusted

Repository content cannot modify platform policy, enable tools, grant network access, authorize execution, or override `AGENTS.md`, `docs/TRUST-MODEL.md`, or operator decisions.

### 13.3 Credentials

Discover MUST NOT accept provider tokens, forge tokens, API keys, database passwords, or route secrets in public arguments.

### 13.4 Network

Network use is provider-specific and operator-configured. Callers may not supply arbitrary URLs or endpoints. Normal local Discover phases require no network access.

### 13.5 Process boundary

Pure analyzers may run in-process only when they do not execute target code, import target projects, spawn processes, or use the network. Process-backed analyzers are Work operations behind fixed manifests, approved executable resolution, bounded I/O, timeout, isolated state, and no caller-provided environment or endpoint.

### 13.6 Provider failures

Provider failure MUST degrade only the affected capability. Deterministic local evidence remains valid. Required capability failure must be explicit and bounded.

## 14. Health, observability, and performance

Discover health SHOULD report runtime readiness, active profile, configuration fingerprint, registry fingerprint, enabled and ready capability counts, supported languages and analyzers, provider readiness, index freshness, harvest status, degraded capabilities, execution-disabled state, and schema versions.

Health MUST NOT expose secrets, raw credentials, sensitive paths, arbitrary environment values, or stack traces.

Initial scale targets one repository or bounded monorepo beneath `C:\Projects`, deterministic cold inspection under configured budgets, Git-aware narrowing, no mandatory vector database, and no mandatory background indexer.

Optimization order:

1. exclusions and identity boundaries;
2. manifest-first detection;
3. Git-aware narrowing;
4. cached file metadata and parse products;
5. semantic-provider indexes;
6. optional vector retrieval.

Generated caches remain beneath `C:\Projects\.kis-mcp` and are never repository authority.

### 14.1 Implementation checkpoint — 2026-08-05

| Area | v1 status | Boundary |
|---|---|---|
| D0 contracts, read authority, budgeting, architecture, and harvest traceability | Complete | Deterministic local foundation |
| D1 repository intelligence and public `inspect_project` | Complete | Bounded local repository evidence |
| D2 local change intelligence and public `inspect_change` | Complete | Working tree, staged, commit, range, and branch targets; remote PR/MR evidence remains provider-dependent |
| D3 semantic code intelligence | Staged | Python AST plus static JavaScript/TypeScript relationships are available; optional Serena/LSP/SCIP providers are not required for local v1 readiness |
| D4 context broker and public `get_code_context` | Complete | Explicit task and budget; no repository dump |
| D5 verification intelligence and Work handoffs | Complete for local declarations | Discover does not execute checks |
| D6 provider harvesting and admission | Local evidence foundation complete | Explicit checked-in candidate manifest, pending Govern request, and non-executing Work plan; installation and activation remain prohibited |
| D7 API and contract intelligence | Initial local foundation complete | OpenAPI JSON, JSON Schema, and checked-in MCP contract classification; additional formats remain staged |
| D8 cross-repository discovery | Local explicit-selection foundation complete | No implicit `C:\Projects` scan; indexes and provider-backed cross-repository impact remain staged |

The bounded local Discover v1 completion gate is the three public workflows, their deterministic local fallbacks, explicit degradation, and internal governed evidence foundations. Optional provider-backed expansion remains roadmap work and MUST NOT be represented as installed or ready until separately admitted and verified.

## 15. Delivery roadmap

### Phase D0 — Contract and boundary consolidation

- adopt this specification;
- define Discover evidence, finding, recommendation, unknown, relationship, provider, verification, and handoff contracts;
- establish `ReadAuthority`, result budgeting, service composition, and architecture tests;
- preserve Work behavior and the three-rule decision set;
- record source harvesting and parity evidence.

### Phase D1 — Repository intelligence parity

- implement `inspect_project` in the existing `kis-mcp` runtime;
- adapt sdk-tool analysis and project-intelligence foundations;
- port dev-intel scanner, topology, detectors, Git, confidence, unknowns, connector requests, and compaction behavior;
- detect verification and API or schema artifacts;
- include bounded pure Python structural indexing;
- prove deterministic self-inspection and fixture parity;
- add the public contract and tool registration seam.

### Phase D2 — Change intelligence

- implement `inspect_change` for working tree, staging, refs, commits, and branch comparisons;
- add changed-symbol, dependent-module, contract, documentation, and test-impact mapping;
- produce typed verification handoffs;
- integrate bounded GitHub pull-request and check evidence;
- add GitLab merge-request and pipeline evidence.

### Phase D3 — Semantic code intelligence

- evaluate and integrate Serena as the first read-only semantic provider;
- normalize symbol, reference, implementation, and diagnostic contracts;
- add provider health and deterministic fallback behavior;
- evaluate LSP, SCIP, Ctags, Sourcegraph, Greptile, and other provider options;
- persist bounded Code Atlas, Symbol Atlas, and Relationship Graph state under the central state root.

### Phase D4 — Context broker

- implement `get_code_context` with explicit budgets;
- rank deterministic repository, symbol, Git, instruction, test, and contract evidence;
- report unknowns and omissions;
- add context-quality fixtures and regression tests.

### Phase D5 — Verification intelligence and Work handoff

- complete verification inventory across supported ecosystems;
- add verification graph and missing-test recommendations;
- create typed Work handoffs;
- consume normalized Work execution results;
- add CI evidence and artifact references.

### Phase D6 — Provider harvesting and admission

- add candidate adapters for local repositories, approved plugin corpora, registries, GitHub, and GitLab;
- normalize descriptors and aliases;
- add license, maintenance, effect, schema, overlap, risk, and trust evidence;
- generate Work conformance plans and Govern admission requests;
- add immutable provider manifests and locks.

### Phase D7 — API and contract intelligence

- implement OpenAPI topology and code or test linking;
- add contract coverage and drift findings;
- generate adapter proposals without activation;
- add remote-MCP conformance evidence through Work;
- extend to JSON Schema, GraphQL, Protobuf and gRPC, AsyncAPI, and database contracts.

### Phase D8 — Cross-repository and indexed discovery

- add optional multi-repository identity and relationship mapping;
- support approved Sourcegraph, SCIP, or equivalent indexes;
- add bounded cross-repository change impact;
- preserve repository-level authorization and evidence provenance.

## 16. Acceptance criteria

Discover is product-ready when:

1. `inspect_project` classifies supported repositories without reading them wholesale.
2. Every material finding and recommendation resolves to returned evidence.
3. Filesystem and Git inspection pass link, path, hard-link, race, size, timeout, and output-boundary tests.
4. Local and remote identities are validated before evidence is merged.
5. `inspect_change` identifies changed files, symbols, likely dependants, relevant tests, and required checks under explicit budgets.
6. `get_code_context` returns materially relevant bounded context and reports omissions.
7. Discover does not execute repository code, arbitrary commands, tests, builds, browsers, package managers, or provider installers.
8. Verification discovery produces typed Work handoffs without caller-controlled executable paths or arbitrary commands.
9. Provider candidates preserve source, revision, license, capabilities, effects, authentication, trust, overlap, and conformance evidence.
10. No provider is activated solely from a registry or marketplace listing.
11. Provider failure produces bounded degradation and actionable diagnostics.
12. Output ordering is deterministic for identical inputs except declared temporal fields.
13. Generated state remains outside repositories.
14. Work continues to enforce exactly HR-001, HR-002, and HR-003.
15. Testing boundaries remain explicit: Discover discovers, Govern requires, Work executes.

## 17. Product risks and trade-offs

| Risk or tension | Decision |
|---|---|
| Provider abundance versus product coherence | Keep providers behind normalized capabilities and a small workflow surface. |
| Semantic depth versus portability | Start with Serena, preserve parser and Git fallbacks, and keep contracts provider-neutral. |
| Discovery versus execution | Keep pure analysis in Discover and process-backed operations in Work. |
| Broad recommendations versus tool sprawl | Recommend gaps and capabilities before providers; prefer the smallest approved provider. |
| Local determinism versus remote freshness | Keep local evidence primary; make remote evidence optional, identity-checked, and freshness-aware. |
| Deterministic relationships versus embeddings | Keep files, symbols, references, dependencies, Git, tests, and contracts primary. |
| Consolidation versus rewrite | Adapt proven sdk-tool and dev-intel behavior with parity tests; do not retain sibling runtime dependencies. |
| Complete roadmap versus oversized first slice | Preserve the full target here and implement one independently reviewable phase at a time. |

## 18. Definition of done

The bounded local Discover v1 module is complete when an agent can use the fixed three-workflow surface to:

- establish canonical local project and repository identity;
- understand bounded repository structure, languages, frameworks, modules, entry points, supported contracts, tests, CI declarations, instructions, documentation, governance artifacts, and local Git state;
- retrieve exact task-relevant files, Python symbols, static local relationships, and constraints under an explicit budget;
- inspect working-tree, staged, commit, range, and branch changes and understand deterministic or explicitly heuristic impact;
- produce an evidence-backed verification plan without executing it;
- identify missing capabilities and assemble bounded provider-admission evidence without installing or approving a provider;
- map relationships only among explicitly selected local projects without scanning the project root implicitly;
- preserve provenance, confidence, unknowns, omissions, and truncation;
- hand policy questions to Govern and execution or mutation to Work;
- pass public contract, architecture, isolation, determinism, security, and full repository verification.

Optional provider expansion is complete only after separately approved semantic, forge, additional contract, registry, or indexed providers are admitted, verified, and proven through their own contracts. Those later capabilities extend Discover v1; their absence does not weaken or misrepresent the completed deterministic local runtime.

## 19. Source and decision traceability

### Authoritative kis-mcp sources

- [`../AGENTS.md`](../AGENTS.md);
- [`../SPEC.md`](../SPEC.md);
- [`TRUST-MODEL.md`](TRUST-MODEL.md);
- [`PLATFORM-CONCEPT.md`](PLATFORM-CONCEPT.md);
- [`../policy/kis-mcp.policy.json`](../policy/kis-mcp.policy.json).

### Approved source specifications

- operator-supplied `DISCOVER-MODULE-PRODUCT-SPEC.md`, dated 2026-08-01;
- operator-supplied `SDK-PLATFORM-CONCEPT.md`;
- the approved decision to use sdk-tool Phase 1 and Phase 2 as the primary Discover baseline.

### Pinned local donor evidence

- `sdk-tool` `feat/phase2-project-intelligence` at `fd1e6a7ab3dac31463aaf1340656df41542f446b`;
- `sdk-tool` progressive discovery baseline at `9832a1f` and Serena plan at `a058464`;
- `dev-intel-tool` at `26d1a2f`, including inspect hardening from `ae73081`;
- `mcp-tool` stable baseline at `246fb10`, with later structured diagnostic patterns reviewed separately.

These donors are implementation evidence. `kis-mcp` contracts, configuration, tests, and operator-approved authority remain controlling.
