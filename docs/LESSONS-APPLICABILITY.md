# Prior-Project Lessons Applicability

## Status

Supporting engineering and governance guidance for `kis-mcp`.

This document records how the consolidated prior-project recommendations apply to the current repository. It is not policy authority, does not add an enforcement rule, and does not convert advisory review practices into authorization gates. When it conflicts with `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, or the machine-readable policy, the higher authority wins.

## Decision model

Each lesson is classified as one of:

- **Applied now** — relevant to the current Work-plane baseline and represented in repository authority, implementation, tests, or operations.
- **Adopted for future phase** — approved in the platform target, but not current behavior.
- **Advisory trigger** — a development or review practice, not a runtime restriction.
- **Not applicable now** — outside the current implementation slice.
- **Rejected for this scope** — conflicts with the supervised three-rule model or would duplicate an upstream provider.

## 1. Product doctrine and policy

| Lesson | Classification | Repository application |
|---|---|---|
| Private, single-operator, directly supervised trust model | Applied now | Defined in `AGENTS.md`, `docs/TRUST-MODEL.md`, and `SPEC.md`. |
| Tool capability and policy are separate | Applied now | Desktop Commander provides capability; FastMCP resolves effects and applies only HR-001 through HR-003. |
| Preserve a complete useful provider surface | Applied now | Network-only tools may be omitted because every invocation violates HR-002; mixed-purpose and powerful tools remain available. |
| Evaluate intent and effects, not names | Applied now | Provider-specific parsing is isolated from the provider-neutral policy core. |
| Exactly three prohibited outcomes | Applied now | Enforced by configuration validation and the closed decision set. No lesson in this document creates a fourth rule. |
| Reads outside `C:\Projects` are not prohibited by HR-001 | Applied now | The write boundary remains distinct from retrieval or exposure controls. |
| Indirect writes, child processes, logs, caches, generated outputs, and directory-entry mutations count as writes | Applied now, bounded by resolver coverage | Explicitly resolved effects must be tested. Unknown or speculative side effects are not an independent reason to block. |
| External network through concrete command targets, resolved Git remotes, and explicit package sources counts | Applied now, bounded by resolver coverage | HR-002 requires a proven consuming operation and external target. Inert URLs, package-manager categories, unresolved aliases, and unknown commands remain allowed. Operator bootstrap and approved connectors remain separate paths. |
| Delete-like operations become quarantine moves | Applied now | Safe in-boundary deletion is transformed; unsafe transformation is rejected. Permanent disposal remains outside Work. |
| Hard-rule changes require explicit operator approval and renewed conformance | Applied now | Authority documents require explicit approval. Runtime commissioning must use controlled restart and fresh tests. |
| Outcome-based conformance, including indirection and child processes | Applied now and ongoing | Current tests cover known shapes; every provider upgrade or new mutating shape must extend coverage. |

## 2. Current architecture

| Lesson | Classification | Repository application |
|---|---|---|
| Keep the domain core independent from MCP SDKs | Applied now | Policy, paths, models, quarantine, provider readiness, and command intent are separate modules. |
| Backends are adapters, not owners of product policy | Applied now | Desktop Commander adaptation belongs in `desktop_commander.py` and middleware; policy decisions remain provider-neutral. |
| Reuse provider-native functionality instead of recreating it | Applied now | Desktop Commander is installed externally and is not vendored, forked, or replaced. |
| Keep settings, policy, secrets, and implementation separate | Applied now | Settings and policy use separate JSON files; credentials and generated state are excluded from repository authority. |
| Centralize runtime state | Applied now in target configuration; repository hygiene requires attention | Canonical runtime state is `C:\Projects\.kis-mcp`. Repository-local `.mcp-command-state` and `.pytest_cache` are generated artifacts and must remain ignored and non-authoritative. |
| One shared filesystem authority | Applied now | Path resolution and boundary decisions are centralized rather than implemented independently per tool. |
| Deterministic ordering, bounded collections, deadlines, and explicit truncation | Applied now and ongoing | Discover, Skills, provider runtime, the advisory agent, and Control Center use bounded deterministic contracts. Govern and future workflows must preserve the same rule. |
| Portable JSON contracts and backend parity | Applied now, bounded | Discover, Skills, Provider runtime, agent, and Control Center settings and responses use versioned JSON contracts. Semantic parity across future providers remains continuing work. |
| Provider, language, analyzer, and workflow registries | Partly applied now | Provider, Tools, Skills catalogue, and internal Discover analyzer registries are implemented. A broad language registry and general workflow coordinator remain target work. |
| Separate installed, enabled, authorized, ready, mounted, exposed, and commissioned states | Applied now | Provider status separates registration, runtime enablement, readiness, build/mount, user action, and commissioning. None may become a fourth reason to block ordinary Work. |
| Evidence-driven modularity; avoid both monoliths and premature splitting | Advisory trigger | Use change evidence, dependency direction, co-change, and blast radius before introducing or splitting modules. |

## 3. Tool surface and usability

| Lesson | Classification | Repository application |
|---|---|---|
| Flat catalogues and full schemas consume context | Partly applied now; progressive exposure remains target | Skills and Provider catalogues project bounded metadata, while the primary gateway still exposes the active tool surface. Do not duplicate Desktop Commander wrappers merely to create another catalogue. |
| Small discovery surface and on-demand descriptions | Partly applied now | Gateway-native surfaces remain bounded; Skills supports search/load, and Provider metadata is separate from construction. Broader progressive public exposure remains target work. |
| Stable IDs, explicit versions, and deprecation lifecycle | Applied now and ongoing | HR IDs, gateway errors, module schemas, provider records, Discover contracts, Skills settings, agent settings, and Control Center settings are versioned. Future contract changes require explicit compatibility handling. |
| Complete metadata for SDK-native tools | Partly applied now; future expansion | Gateway-native operations must document purpose, effects, bounds, recovery, and errors. Provider-native tools retain native contracts. |
| Corrective errors without raw diagnostics or secrets | Applied now | Public rejections should identify the violated rule, invalid field or path, safe correction, and retryability without exposing sensitive state. |
| Capability-group size and overlap reviews | Advisory trigger | The historical 12-tool threshold is a review prompt only and is not policy. |

## 4. Development and verification discipline

The following are engineering controls, not runtime authorization rules.

| Lesson | Classification | Repository application |
|---|---|---|
| Start substantial work from approved design and explicit acceptance criteria | Advisory trigger | Required for implementation phases and architecture changes. |
| Test behavioral changes first and preserve failing evidence | Advisory trigger | Use for executable changes under the repository development workflow. |
| Keep one logical reason for change per change unit | Advisory trigger | Split feature, refactor, dependency, and identity changes when their evidence or rollback differs. |
| Estimate blast radius and run modularity assessment before large refactors | Advisory trigger | Trigger when changes cross modules, alter dependencies, add top-level packages, or change public contracts. Numeric historical thresholds are guidance only. |
| Do not weaken verification, skip failures, add broad exclusions, or bypass hooks | Applied now as repository practice | A green result obtained by suppressing evidence is not completion. |
| Verification must not leave unexplained repository mutations | Applied now as repository practice | Inspect generated state, status, and ignored artifacts after verification. |
| Focused tests do not replace the canonical repository gate | Applied now | `scripts/verify.ps1` remains the completion entry point; transport smoke and provider parity are additional when applicable. |
| Configuration must validate before server bind | Applied now | Startup loads and validates settings and exact rule IDs before operation. |
| Fresh evidence is required for completion claims | Applied now | Report exact commands, results, and unverified areas. |
| Separate facts, inferences, assumptions, recommendations, and unchecked gaps | Applied now as review standard | Audits and handovers must make evidence status explicit. |

## 5. Review triggers

These triggers require review or renewed verification. They do not independently authorize or prohibit a Work invocation.

| Trigger | Required response |
|---|---|
| Hard-policy or policy-configuration change | Obtain explicit operator approval, validate exactly HR-001 through HR-003, restart through the controlled lifecycle, and rerun outcome conformance. |
| Desktop Commander version, schema, or launch change | Rerun provider readiness, mapping, bypass, mutation, network, deletion, and end-to-end forwarding tests. |
| New provider or backend | Confirm provider isolation, portable contracts where applicable, semantic parity, and all three outcome tests. |
| New mutating, network-capable, deletion-capable, or command shape | Add provider-adapter resolution and negative tests before claiming coverage. |
| Public contract or error-code change | Review compatibility, stable identifiers, migration, documentation, and backend parity. |
| New top-level package or dependency-direction change | Record the architecture decision and reassess module ownership and blast radius. |
| Change crossing multiple modules or a large refactor | Run a formal modularity assessment before implementation. |
| New SDK-native tool | Add metadata, examples, effects, limits, recovery, tests, policy interaction, documentation, and exposure decision in the same change. |
| Capability group growth or material overlap | Perform consolidation or split review; do not treat the review threshold as a hard rule. |
| Authority-document conflict or doctrine change | Run repository-wide searches for stale names, IDs, paths, restrictions, and implementation claims. Preserve superseded history as historical rather than silently rewriting it. |
| Phase completion, PR readiness, merge, or release | Run fresh applicable verification, inspect full diff and status, record skipped checks, and distinguish target from commissioned behavior. |

## 6. Documentation and authority

| Lesson | Classification | Repository application |
|---|---|---|
| One governed fact should have one authoritative source | Applied now | `AGENTS.md` defines order; trust rules belong in `docs/TRUST-MODEL.md` and machine enforcement in policy JSON. This document only maps applicability. |
| Historical plans must be labelled non-authoritative when superseded | Applied now as governance practice | Preserve history without allowing it to override current authority. |
| Machine-readable contracts carry enforceable facts; prose explains | Applied now | Policy JSON and configuration validation are executable; prose must not claim enforcement that code and tests do not provide. |
| Stable rule IDs connect documentation, code, configuration, and tests | Applied now | HR-001, HR-002, and HR-003 are the only accepted policy IDs; unknown IDs fail validation. |
| Generated views are non-authoritative and deterministic | Adopted for future phase | Applies when platform catalogues, evidence views, reports, or generated documentation are introduced. |
| Documentation must distinguish target and current implementation | Applied now | `SPEC.md` owns the baseline; `docs/PLATFORM-CONCEPT.md` owns the target state. |
| Repository-wide search and status inspection after doctrine changes | Applied now as completion practice | Search for stale identity, paths, rule IDs, prohibitions, and capability claims; inspect untracked and ignored state where tooling permits. |

## 7. Delivery priorities

| Lesson | Classification | Repository application |
|---|---|---|
| Build the smallest useful replacement first | Applied now | The Work gateway was established first; later modules were added as bounded independent slices. |
| Do not import stale predecessor implementation | Applied now | Donor repositories remain source material only, never runtime dependencies. |
| Adopt providers and tools rather than recreating them | Applied now | Desktop Commander, GitHub MCP, Supabase, NVIDIA NIM, Codex CLI, AgentSys, and agnix retain distinct authoritative boundaries and integration states. |
| Discover and Govern must not delay useful Work | Applied now | Work remained useful while Discover was added incrementally; Govern remains target work rather than a prerequisite for ordinary supervised Work. |
| Deterministic local features should not require model or network calls | Applied now and ongoing | Public and internal Discover, Skills, provider metadata, and Control Center use local deterministic evidence. Model calls are confined to the optional advisory agent. |
| Pure analysis before process-backed analysis | Applied now and ongoing | Discover uses bounded file, Git, and AST/static analysis without executing repository code. Future execution-backed analyzers require separate contracts and authority. |
| Stop when the approved bounded capability is complete and verified | Applied now | Optional expansion is deferred unless separately approved and claimed. |

## 8. Rejected or constrained lessons

The following interpretations are explicitly rejected for the current scope:

- treating powerful, destructive-looking, mixed-purpose, terminal, or process tools as prohibited by category;
- tool-name, executable-name, or command-name blacklists as policy decisions;
- allowlist-only architecture that blocks otherwise permitted provider operations;
- readiness, registration, profile, catalogue, review, governance, or evidence state as a fourth Work prohibition;
- mandatory Discover or Govern gates before ordinary directly supervised Work;
- recreating, forking, or extensively wrapping Desktop Commander without explicit operator approval;
- importing predecessor runtime code or carrying old and new architectures indefinitely;
- treating historical numeric review thresholds as hard policy;
- claiming complete containment of unknown command side effects when only explicit intent and supported effect shapes are resolved;
- claiming target platform capabilities as commissioned current behavior.

## 9. Current coverage assessment

### Strongly covered

- closed trust model and exactly three prohibited outcomes;
- separation of provider capability, effect resolution, and policy decisions;
- provider reuse and greenfield boundary;
- strict JSON settings, policy, and versioned contracts;
- quarantine and restoration;
- public bounded Discover through `inspect_project` and working-tree `inspect_change`;
- shared Skills catalogue and Work-backed mutation;
- Provider registry, catalogue, readiness, runtime composition, and status;
- optional NVIDIA/Codex advisory review workflow;
- supervised pinned AgentSys and agnix bootstrap with isolated managed state and recoverable activation;
- standalone read-only Control Center;
- current-versus-internal-versus-standalone-versus-target documentation boundaries;
- canonical verification entry point.

### Covered but requiring continuing evidence

- complete Desktop Commander schema mapping and provider-upgrade conformance;
- command and child-process effect resolution across supported shapes;
- links, junctions, relative paths, redirects, generated files, and indirect writes;
- live provider authentication, upstream connectivity, and end-to-end forwarding;
- live NVIDIA inference and Codex authentication;
- tunnel credential/profile presence, ChatGPT discovery, and remote smoke evidence;
- generated-state containment and post-verification repository cleanliness;
- public composition and compatibility of internal Discover services.

### Implemented internally but not public gateway tools

- staged, commit, range, and branch change-target readers;
- context brokering;
- impact analysis, dependant mapping, affected tests, and verification handoffs;
- contract intelligence;
- explicit project cataloging;
- provider-admission evidence with a fixed pending-Govern boundary.

### Correctly deferred

- Govern implementation and authority/ruleset evaluation;
- broader semantic providers and language intelligence;
- public context, impact, contract, project-catalog, and provider-admission workflows;
- trusted remote evidence normalization for Discover;
- general workflow coordination and composed review, audit, debugging, and governance surfaces;
- bounded Work planning, proposal, application, and verification workflows beyond ordinary provider operations.

## 10. Completion rule

A lesson is considered applied only when its relevant authority, implementation, tests, operations, or explicit deferral can be identified. Documentation alone does not prove runtime behavior. Future work should update this mapping only when a classification changes; it must not duplicate the authoritative rule or specification text.
