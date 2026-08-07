# kis-mcp Platform Concept

## Status

Approved target product specification for the planned evolution of `kis-mcp`.

This document defines the final platform boundary, capability planes, shared kernel, primary workflows, authority model, provider strategy, profiles, delivery direction, and success criteria. It is a target-state document only: capabilities described here are not implemented merely because they are documented.

The current implementation baseline remains the small operator-supervised FastMCP gateway described in `SPEC.md`. The three prohibited outcomes in `docs/TRUST-MODEL.md` remain the only enforcement restrictions unless the operator explicitly changes them.

The detailed Discover product boundary and phased roadmap are defined in [`DISCOVER-MODULE-PRODUCT-SPEC.md`](DISCOVER-MODULE-PRODUCT-SPEC.md). That document is target-state authority for Discover only; `SPEC.md`, checked-in contracts, tool registration, configuration, and fresh tests remain authoritative for current implementation claims.

## 1. Purpose

The kis-mcp Platform is a governed environment for understanding, evaluating, and changing software repositories.

It combines three bounded capability planes:

```text
kis-mcp Platform
├── Discover
├── Govern
└── Work
```

The planes operate through one shared platform rather than three independent products.

- **Discover** establishes evidence about a repository, codebase, change, or trusted external repository context.
- **Govern** evaluates that evidence against declared repository standards and authority rules.
- **Work** performs controlled operations based on approved evidence, decisions, and the three-rule enforcement boundary.

Repository discovery, code intelligence, reviews, audits, debugging, security analysis, documentation governance, and implementation are composed workflows over these planes, not separate foundational products.

## 2. Core design decision

The final platform MUST use:

- one runtime;
- one project identity model;
- one policy engine;
- one evidence model;
- one provider registry;
- one progressive tool catalogue;
- one result and error contract;
- separate capability planes with explicit authority boundaries.

The platform MUST NOT duplicate scanners, policy logic, evidence formats, or repository identity across separate services unless deployment isolation later requires it.

```text
Discover establishes facts.
Govern evaluates facts against declared standards.
Work performs controlled changes.
```

Reviews and audits are composed workflows over these planes.

## 3. Relationship to the current kis-mcp baseline

The current gateway is no longer only the initial Work-plane foundation. It now contains bounded public Discover, capability-bearing Skills, Provider and Tool composition, a normalized capability catalogue, readiness-aware progressive exposure, first-class workflow descriptors and recommendations, effect-specific long-tail dispatch, and a read-only Control Center available both mounted and standalone. Govern and broader executable workflow orchestration remain target-state capabilities.

### Current capability state

| State | Capability |
|---|---|
| Direct primary profile | Frequent Work and Discover operations; health and provider status; capability search, description, and workflow recommendation; effect-specific dispatch; advisory review when ready; and the mounted Control Center entry point. |
| Discoverable catalogue | Remaining valid Desktop Commander, Skills, internal Discover, quarantine, and mounted provider operations with original schemas, readiness, effects, quality, and exposure metadata. |
| Status-only catalogue | Disabled, unavailable, authentication-gated, build-failed, or mount-failed operations remain visible but ineligible. |
| Standalone | KIS Control Center read-only MCP App and UI resource using the same evidence model. |
| Managed support tooling | AgentSys `6.0.1` host profiles and agnix `0.45.0` CLI are installed through supervised bootstrap scripts and remain outside gateway composition. |
| Target | Govern surface, broader semantic and trusted remote evidence, and additional executable workflow coordination. |

The current implementation remains responsible for:

- integrating the authoritative Desktop Commander distribution;
- resolving concrete invocation effects;
- enforcing exactly HR-001, HR-002, and HR-003;
- preserving ordinary local development operations outside those prohibited outcomes;
- providing recoverable quarantine;
- exposing bounded local Discover evidence without executing repository code;
- resolving the approved shared Skills catalogue and routing its mutations through Work;
- explicitly registering and composing approved providers;
- keeping provider-client authentication lifetime independent from repository-specific routing and selection;
- exposing one bounded advisory code-review workflow without mutation authority;
- composing all domains through normalized immutable capability contributions;
- separating registration, readiness, recommendation, and exposure;
- preserving the long tail through effect-specific dispatch and original middleware while keeping the direct tool-schema surface bounded.

The future platform may add Govern, broader semantic and trusted remote evidence, and executable coordination for more declared workflows. Those additions MUST NOT silently create a fourth policy prohibition.

Profiles, catalogues, governance checks, evidence requirements, readiness states, and workflow routing may control what platform functionality is installed, selected, or presented. They MUST NOT be interpreted as independent reasons to block an otherwise permitted Desktop Commander invocation under the three-rule Work policy.

### Implemented Skills capability

The current platform includes a focused `skills.catalogue` capability. It resolves reusable procedures from `C:\Projects\.agents\skills`, enriches every current runtime card with reviewed category, capability, activation, effect, and workflow metadata from JSON, exposes bounded catalogue and read/evaluation operations, and routes create/improve mutations through the existing Work middleware and Desktop Commander backend. Skills remain reusable procedures rather than repository authority, provider plugins, or new policy rules. ChatGPT loads instructions and composes ordinary Work operations; the runtime does not automatically execute arbitrary skill code. Initial catalogue failure leaves the wider Work/gateway server available and surfaces a corrective Skills error.

### Implemented Provider and agent capability

The Provider registry contains Desktop Commander, GitHub MCP, NVIDIA NIM, Supabase, and Control Center descriptors. GitHub, Supabase, and Control Center may mount under namespaced operations; NVIDIA is workflow-only. Codex CLI remains a local Tools-registry adapter. Each gateway owns its exact Provider and capability composition state; no global latest-composition singleton remains. The Provider platform also owns mutable selected-repository state separately from provider authentication lifetime. GitHub uses one shared FastMCP client for the parent runtime, performs one `get_me` bootstrap after connection, reuses that authenticated process across downstream sessions, and resolves repository/Project authorization from the current repository settings on each call. Readiness, mounting, authentication, commissioning, recommendation, and exposure are reported separately and do not create Work authorization.

`review_change_with_agent` collects bounded local Git evidence and requests one advisory review through NVIDIA NIM or Codex CLI. It permits at most one fallback and grants no mutation or nested-delegation authority.

### Control Center

The KIS Control Center is a read-only MCP App available through the mounted `controlcenter_*` provider and through a standalone process. It reports bounded local runtime, project, policy, provider-configuration, quarantine, and verification guidance. The mounted form receives explicit instance-scoped provider status and remains outside Work authorization.

## 4. Shared platform kernel

```text
kis-mcp Platform Core
├── ProjectIdentity
├── ReadAuthority
├── PolicyEngine
├── EvidenceStore
├── ResultBudgeter
├── ProviderRegistry
├── ToolCatalogue
├── WorkflowCoordinator
└── VerificationRegistry
```

### ProjectIdentity

Resolves the canonical local project, Git repository, remote repository, workspace boundaries, and trusted external context.

The current baseline partially implements this through strict repository-local settings: `settings/kis-repository.settings.json` declares repository identity, `github_repository`, and `gh_projects`; the loader validates the GitHub identity against local `origin` when available; and Provider composition retains a mutable selected-repository source independently of authenticated provider-client lifetime. Broader cross-repository identity and trusted external context remain target-state work.

### ReadAuthority

Applies declared read boundaries, exclusions, file limits, traversal rules, and protected-path handling. Read controls are retrieval and exposure rules, not additions to HR-001 through HR-003.

### PolicyEngine

Determines installed, enabled, runtime-ready, and exposed platform capabilities. For Work invocation enforcement, the closed decision set remains the three rules defined in `docs/TRUST-MODEL.md` and `policy/kis-mcp.policy.json`.

### EvidenceStore

Implemented for work-management review evidence and partially implemented elsewhere. Review artifacts are normalized beneath `.work/reviews/<review-id>/`, validated against canonical manifests, bounded by strict settings, written through atomic replacement, and protected by hash-based conflict detection. Broader cross-domain evidence indexing remains future work.

### ResultBudgeter

Bounds files, symbols, characters, findings, diagnostics, relationships, and external evidence returned to the caller.

### ProviderRegistry

Manages optional providers such as Desktop Commander, local filesystem readers, Git, semantic engines, GitHub connectors, `gh` CLI, PR review providers, and future indexed-code providers.

### ToolCatalogue

Implemented for the current gateway. Provider, Tool, Discover, Skill, and Workflow platform entry points contribute normalized immutable metadata. Eligibility filters readiness, dependencies, credentials, effects, and enablement before deterministic explainable scoring. A JSON-bounded direct profile limits default tool-schema context while the valid long tail remains searchable and effect-dispatched through original schemas and middleware.

### WorkflowCoordinator

Partially implemented as first-class workflow descriptors, `recommend_workflow`, the advisory code-review workflow, and bounded P5 project-management orchestration. Current descriptors cover isolated development, change review, safe pull-request closeout, worktree cleanup, provider commissioning and diagnosis, skill creation or improvement, modularity assessment, work capture, review-evidence persistence, Project reconciliation, programme status, and traceability verification. Project-management tools remain disabled until strict settings are enabled and a valid backend binding is commissioned; broader general-purpose orchestration remains future work.

### VerificationRegistry

Discovers and records approved repository verification commands, CI checks, governance checks, and provider-health evidence.

## 5. Discover plane

### Purpose

Discover determines what exists and retrieves only the evidence required for the current task.

```text
Discover
├── repository discovery
├── code atlas
├── symbol atlas
├── dependency and reference relationships
├── manifests, frameworks, and build systems
├── instructions and documentation
├── local Git evidence
├── trusted remote GitHub and PR evidence
├── diagnostics
└── task-scoped context broker
```

### Primary workflows

#### `inspect_project`

Returns bounded repository-wide evidence, including:

- project identity and topology;
- languages, manifests, frameworks, package managers, and workspaces;
- modules and entry points;
- build, test, lint, type-check, and verification declarations;
- CI and repository instructions;
- documentation and governance artifacts;
- local Git summary;
- trusted connector context;
- findings, confidence, provenance, and truncation state.

#### `inspect_change`

Evaluates a working-tree change, commit range, branch comparison, or pull request and returns changed files and symbols, affected modules and dependants, likely contract changes, affected tests, verification requirements, governance impact, remote review evidence, risk areas, and relevant workflows.

#### `get_code_context`

Returns task-specific code context under an explicit budget. It combines relevant modules, symbols, relationships, files, tests, instructions, unknowns, provenance, and truncation status without flattening the repository into one large prompt.

### Code intelligence layers

```text
Code atlas
    ↓
Symbol atlas
    ↓
Context broker
```

The code atlas maps files, modules, packages, imports, dependencies, central modules, entry points, generated files, tests, instructions, and ownership metadata.

The symbol atlas maps classes, functions, methods, signatures, declarations, implementations, references, inheritance, imports, exports, diagnostics, and optional call relationships.

The context broker combines repository, symbol, Git, instruction, and verification evidence for one bounded task.

Provider-specific schemas remain behind normalized kis-mcp contracts. Semantic and deterministic evidence remains primary; embeddings may supplement but not replace symbols and references.

## 6. Govern plane

### Purpose

Govern defines and verifies what a repository is supposed to look like.

```text
Govern
├── authority and ownership rules
├── repository structure standards
├── documentation placement
├── AGENTS.md scope and quality
├── README scope and quality
├── canonical-document ownership
├── code-as-docs contracts
├── policy and configuration boundaries
├── required verification
├── drift detection
├── exception tracking
└── compliance evidence
```

Govern depends on Discover but remains a separate authority domain.

```text
Discover: What is present?
Govern:  Is it correct, complete, current, and authoritative?
Work:    What controlled action should change it?
```

### Code-as-docs model

Repositories may contain source code, machine-readable contracts, generated documentation, human orientation, agent instructions, authority metadata, and verification evidence.

| Artifact | Primary authority |
|---|---|
| `AGENTS.md` | Agent constraints, workflow routing, and repository-specific operating instructions |
| `README.md` | Human orientation, purpose, setup, and links to canonical detail |
| Architecture documents | Stable boundaries, decisions, dependency direction, and system structure |
| Source and docstrings | Implementation-level contracts and behavior |
| Generated API documentation | Derived, non-authoritative representation of source contracts |
| Policy files | Machine-enforced authorization and operational constraints |
| Governance manifest or registry | Canonical ownership, locations, required artifacts, and authority declarations |
| CI workflows | Executable verification of repository rules |
| Skills | Reusable procedures, not repository-specific authority |

### Governance findings

The platform should detect duplicated or conflicting authority, facts stored in the wrong canonical location, agent rules placed in general human documentation, manually edited generated artifacts, missing ownership declarations, stale diagrams or capability claims, undocumented public contracts, conflicts between instructions and exposed tools, missing required verification, repository drift, and unrecorded exceptions.

### Initial public governance surface

- `list_governance_capabilities`
- `inspect_repository_governance`
- `evaluate_governance_rules`
- `describe_governance_finding`

Specialized governance reviews should normally be workflows or rulesets rather than many separate public tools.

## 7. Work plane

### Purpose

Work performs controlled operations based on discovered evidence, governance decisions, explicit operator authority, and the three-rule enforcement boundary.

```text
Work
├── ordinary Desktop Commander operations
├── plan changes
├── propose bounded patches
├── apply approved changes
├── run fixed verification workflows
├── create branches and commits
├── perform bounded GitHub operations
├── generate documentation
└── produce implementation artifacts
```

### Authority rules

- Work MUST NOT determine its own authority.
- Read and mutation capabilities MUST remain separate at the platform-contract level.
- Work SHOULD consume evidence produced by Discover and decisions produced by Govern.
- Mutations MUST be auditable, bounded, and recoverable where practical.
- The Work enforcement boundary MUST block or transform only HR-001, HR-002, or HR-003.
- Tool names, broad capability, destructive-looking metadata, approval tiers, profile membership, catalogue omission, or incomplete static prediction MUST NOT become additional policy rules.
- Arbitrary provider configuration and unrestricted provider passthrough should not be exposed as dedicated public platform workflows, while ordinary provider operations remain available subject only to the three hard rules.

### Initial public work surface

- `list_workflows`
- `plan_change`
- `propose_change`
- `run_verification`

Broader filesystem, Git, generation, and execution operations remain supporting provider capabilities behind workflow selection and the existing three-rule policy.

## 8. Reviews, audits, and debugging

Reviews and audits are composed workflows across the three planes.

```text
Request
  ↓
Discover required evidence
  ↓
Apply technical, governance, or security rules
  ↓
Produce findings, confidence, and remediation
  ↓
Optionally invoke controlled Work operations
```

Candidate workflows include:

- `review_repository`
- `review_codebase`
- `review_change`
- `review_architecture`
- `review_documentation`
- `review_governance`
- `audit_security`
- `audit_dependencies`
- `audit_policy`
- `debug_issue`

Each workflow defines evidence requirements, rule packs, severity policy, output contract, and permitted follow-up operations.

## 9. External provider strategy

The platform should initially orchestrate existing capabilities rather than reimplement complete provider surfaces.

```text
Desktop Commander / Git / semantic provider / GitHub connector / gh / PR Review
                                  ↓
                        bounded normalized evidence
                                  ↓
                      identity and trust validation
                                  ↓
             inspect_project / inspect_change / get_code_context
```

Remote evidence must match the canonical local Git remote and carry provenance and trust status. Approved ChatGPT connectors and operator-supervised bootstrap paths remain separate from local Work network operations prohibited by HR-002.

Provider candidates may include Desktop Commander, Serena or another semantic engine, official MCP filesystem and Git patterns, GitHub MCP, MCP Inspector, MCP conformance tooling, Aider RepoMap concepts, SCIP or Sourcegraph indexes, Universal Ctags, and optional vector retrieval.

## 10. Capability groups and profiles

Recommended capability groups:

```text
project.discovery
code.discovery
code.semantic
context.broker
repository.git_read
repository.remote_read
repository.governance
documentation.governance
audit.read
work.plan
work.propose
verification.execution
repository.mutate
skills.catalogue
validation.documents
```

Recommended profile progression:

```text
read
├── filesystem.read
├── project.discovery
├── repository.git_read
└── skills.catalogue

analysis
├── read
├── code.discovery
├── code.semantic
├── context.broker
└── analysis.static

governance
├── analysis
├── repository.governance
├── documentation.governance
└── audit.read

work
├── governance
├── work.plan
├── work.propose
├── verification.execution
└── repository.mutate
```

Profiles support progressive exposure and least unnecessary authority at the platform level. They do not expand the three-rule policy decision set or justify blocking an otherwise permitted ordinary Work invocation.

## 11. Non-goals

The platform will not initially:

- expose every provider tool as a new custom public wrapper;
- duplicate the full GitHub or GitLab product surface;
- flatten repositories into large prompts;
- index `.git`, build outputs, virtual environments, generated state, or caches by default;
- treat generated documentation as independent authority;
- require embeddings for deterministic repository or symbol facts;
- fork or reimplement Desktop Commander;
- introduce policy prohibitions beyond HR-001, HR-002, and HR-003 without explicit operator approval.

## 12. Delivery sequence

The sequence remains architectural guidance, but several foundations are already implemented. Status must be read by exposure level rather than as a binary complete/incomplete flag.

| Capability | Status |
|---|---|
| Desktop Commander integration, three-rule policy, quarantine, and baseline contracts | Public and implemented. |
| Repository-wide `inspect_project`, local Git evidence, and working-tree `inspect_change` | Public and implemented. |
| Staged, commit, range, and branch change readers | Internally implemented; not exposed by the public `inspect_change` signature. |
| Context broker, impact graph, contract intelligence, project catalog, and provider-admission evidence | Internally implemented with versioned contracts; public composition remains target work. |
| Provider registry, runtime-scoped provider client lifecycle, repository-local GitHub routing/selection, GitHub, Supabase, and Control Center runtime mounting, and provider status | Public and implemented. |
| Unified capability contributions, instance-scoped readiness, eligibility, explainable scoring, and progressive exposure | Public and implemented. |
| Skills catalogue, capability-bearing runtime cards, and mutation workflow | Implemented; operations outside the direct profile remain discoverable. |
| First-class workflow descriptors and recommendations | Implemented for eight current task workflows; general server-executed orchestration remains target work. |
| NVIDIA/Codex advisory code-review workflow | Public and implemented; live backend commissioning is separate evidence. |
| KIS Control Center | Implemented as a mounted and standalone read-only MCP App. |
| AgentSys and agnix managed bootstrap | Implemented as supervised, version-pinned host tooling outside gateway composition. |
| Govern plane, authority registry, rule evaluation, and drift detection | Target. |
| Broader semantic providers and trusted remote Discover evidence | Target. |
| General executable review, audit, debugging, proposal, and verification orchestration | Target; current workflow descriptors and recommendations are implemented. |

The next architectural stages are:

1. finish public composition of approved internal Discover services without widening read or execution authority;
2. add Govern authority, rules, findings, exceptions, and documentation-drift detection;
3. turn selected declared workflows into bounded executable orchestration after their evidence and approval contracts are approved;
4. add bounded Work planning, proposal, application, and verification workflows while preserving ordinary Desktop Commander operations;
5. normalize trusted remote evidence through approved connectors;
6. continue provider discovery, conformance, and registry evaluation through isolated slices.

Each stage requires explicit design, implementation, and verification. Documentation of target capabilities is not implementation evidence.

## 13. Success criteria

The platform is successful when an agent can:

1. identify the correct project and authority boundaries;
2. understand a repository without reading it wholesale;
3. retrieve precise symbol and relationship evidence for a task;
4. evaluate repository state against declared governance rules;
5. understand the impact and risk of a change or pull request;
6. select relevant review, audit, debugging, and verification workflows;
7. propose or perform only policy-authorized changes;
8. preserve provenance, confidence, truncation, and recovery information;
9. use a small progressive public platform surface while retaining ordinary provider operations;
10. produce repeatable results across local, Git, semantic, and trusted remote providers;
11. enforce exactly the three approved prohibited outcomes in the Work path.

## 14. Platform statement

The final kis-mcp product is one governed system with three bounded capability planes:

```text
Discover → establish evidence
Govern   → evaluate evidence against declared standards
Work     → perform controlled, authorized change
```

The current FastMCP and Desktop Commander gateway is the initial enforcement foundation of that platform. Repository discovery, code intelligence, governance, reviews, audits, debugging, security analysis, documentation assessment, and implementation are composed workflows built on the shared model.
