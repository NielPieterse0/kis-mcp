# kis-mcp Platform Concept

## Status

Approved target product specification for the planned evolution of `kis-mcp`.

This document defines the final platform boundary, capability planes, shared kernel, primary workflows, authority model, provider strategy, profiles, delivery direction, and success criteria. It is a target-state document only: capabilities described here are not implemented merely because they are documented.

[`../SPEC.md`](../SPEC.md) owns current implementation truth. The three prohibited outcomes in [`TRUST-MODEL.md`](TRUST-MODEL.md) remain the only Work enforcement restrictions unless the operator explicitly changes them.

The detailed Discover target boundary and roadmap are defined in [`DISCOVER-MODULE-PRODUCT-SPEC.md`](DISCOVER-MODULE-PRODUCT-SPEC.md). Current implementation claims remain owned by `SPEC.md` and executable repository evidence.

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

This document defines target architecture only. [`../SPEC.md`](../SPEC.md) owns the current implemented product architecture, capability inventory, provider/tool status, and implementation boundary.

Target design decisions in this document constrain future evolution but do not imply that a capability is implemented. When current and target descriptions differ, treat `SPEC.md` as current truth and this document as the approved destination.

Future platform additions MUST preserve the closed HR-001 / HR-002 / HR-003 Work decision set unless the operator explicitly changes the trust model. Profiles, catalogues, governance findings, evidence requirements, readiness, workflow selection, and presentation may shape platform behavior but MUST NOT become independent Work-policy prohibitions.

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

The target identity model MUST provide stable project IDs, canonical local roots, repository identities, workspace boundaries, provider routing coordinates, and provenance for any trusted external context. One canonical project identity must be reused across planes rather than reconstructed independently by each subsystem.

### ReadAuthority

Applies declared read boundaries, exclusions, file limits, traversal rules, and protected-path handling. Read controls are retrieval and exposure rules, not additions to HR-001 through HR-003.

### PolicyEngine

Determines installed, enabled, runtime-ready, and exposed platform capabilities. For Work invocation enforcement, the closed decision set remains the three rules defined in `docs/TRUST-MODEL.md` and `policy/kis-mcp.policy.json`.

### EvidenceStore

Provides immutable or recoverably superseded evidence with bounded artifacts, integrity metadata, provenance, fingerprints, conflict/corruption detection, and atomic publication. Evidence domains SHOULD reuse this kernel rather than introduce independent persistence semantics.

### ResultBudgeter

Bounds files, symbols, characters, findings, diagnostics, relationships, and external evidence returned to the caller.

### ProviderRegistry

Manages optional providers such as Desktop Commander, local filesystem readers, Git, semantic engines, GitHub connectors, `gh` CLI, PR review providers, and future indexed-code providers.

### ToolCatalogue

Normalizes Provider, Tool, Discover, Skill, and Workflow contributions into one catalogue. Eligibility MUST evaluate readiness, dependencies, credentials, effects, and enablement before deterministic explainable scoring. The platform SHOULD keep the default exposed surface bounded while retaining eligible long-tail capability through governed discovery and dispatch.

### WorkflowCoordinator

Coordinates declared workflows across Discover, Govern, Work, verification, review, and provider boundaries. Workflow descriptions MUST declare evidence requirements, dependencies, effects, completion criteria, and allowed follow-up operations without creating new Work-policy prohibitions.

### VerificationRegistry

Discovers and records approved repository verification commands, CI checks, governance checks, and provider-health evidence.

### Execution substrate

The target platform SHOULD provide a provider-neutral execution substrate beneath verification and selected isolated workflows. Execution profiles may use the existing local process path, disposable Windows guests, or provider-native CI runners, but they MUST preserve the same declared verification identity, bounded evidence, readiness, and provenance semantics.

Disposable Windows execution SHOULD use versioned provider-isolated guests when host-state isolation materially improves correctness or security. VirtualBox is the first commissioning path for the current Windows host, while Hyper-V remains an alternate provider behind the same execution contract. A guest must not inherit mutable development checkout state, KIS runtime state, operator-profile state, host shared folders, or operator credentials by default. VirtualBox global configuration and clone state SHOULD remain beneath the KIS state boundary through an isolated `VBOX_USER_HOME`; network, clipboard/file-transfer, drag-and-drop, VRDE, and USB integration SHOULD be disabled before first guest start. Image identity, exact source identity, toolchain provenance, lifecycle outcome, and bounded diagnostics SHOULD be retained as verification evidence before recoverable guest quarantine or later supervised retirement.

Initial VirtualBox commissioning MUST NOT depend on disabling Hyper-V, VBS, Memory Integrity, Smart App Control, Defender, or equivalent host protections. If coexistence affects correctness or performance, measure it during commissioning and revisit host virtualization configuration as a separate supervised decision rather than silently weakening the host security posture.

GitHub remains the pull-request identity and exact-head merge control plane, not the canonical verification executor. KIS-owned local verification evidence for the exact current pull-request head is the landing gate. Provider-native CI runners may remain optional execution adapters, but GitHub Actions and the speculative Actions-backed queue are dormant and MUST NOT be required for canonical delivery; disposable Windows commissioning evolves independently beneath the provider-neutral execution substrate.

The same outer execution substrate MAY be reused by other registered repositories. In particular, isolation products may compose Docker or another purpose-specific inner sandbox inside a disposable Windows guest rather than replacing their existing containment contracts.

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

For `kis-mcp`, repository-specific document ownership and routing are defined only in [`../AGENTS.md`](../AGENTS.md). Govern must discover and evaluate that declared authority model rather than maintain a second file-by-file ownership table in this target-state document.

The target Govern plane may reason over artifact classes such as source contracts, machine-readable policy/configuration, generated projections, human documentation, verification evidence, and reusable skills. Generated views remain derived from their source, and reusable skills remain procedures rather than repository-specific authority. Any future governance manifest or registry must reference or encode approved ownership without silently superseding the canonical owners declared by repository authority.

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

`SPEC.md` owns current implementation status. This section defines only the target sequencing constraints:

1. establish and keep one shared kernel for identity, evidence, provider registration, capability composition, and verification;
2. complete bounded Discover composition without widening read or execution authority;
3. add Govern authority, rules, findings, exceptions, and documentation-drift detection;
4. turn selected declared workflows into bounded executable orchestration only after their evidence and approval contracts are approved;
5. add bounded Work planning, proposal, application, and verification workflows while preserving ordinary provider operations and the three-rule Work boundary;
6. normalize trusted remote evidence through approved connectors;
7. continue provider discovery, conformance, and registry evaluation through isolated slices.

Each stage requires explicit design, implementation, and verification. Target documentation is never implementation evidence.

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

Repository discovery, code intelligence, governance, reviews, audits, debugging, security analysis, documentation assessment, and implementation are composed workflows built on this shared target model. Consult `SPEC.md` for the current implementation boundary.
