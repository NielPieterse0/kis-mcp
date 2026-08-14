# kis-mcp

Repository: `C:\Projects\kis-mcp`
Remote: `https://github.com/NielPieterse0/kis-mcp.git`

## Canonical identity

- Product name: `kis-mcp`.
- Python distribution and CLI: `kis-mcp`.
- Python import package: `kis_mcp`.
- Runtime settings: `settings/kis-mcp.settings.json`.
- Enforcement policy: `policy/kis-mcp.policy.json`.
- Generated state and quarantine root: `C:\Projects\.kis-mcp`, except the operator-approved agnix runtime compatibility location `C:\Projects\kis-mcp\.temp\tools\agnix`, which remains ignored/untracked and contains no authoritative repository content.

## Authority order

Read these files before changing the repository:

1. `AGENTS.md` — repository scope and operating instructions.
2. `docs/TRUST-MODEL.md` — trust assumptions and the only three prohibited outcomes.
3. `SPEC.md` — current product architecture and implementation boundary.
4. `docs/PLATFORM-CONCEPT.md` — approved final platform outcome and phased evolution.
5. `policy/kis-mcp.policy.json` — machine-readable expression of the three rules.
6. `docs/OPERATIONS.md` — installation, startup, configuration, and verification.

When documents conflict, use the earliest applicable authority above.

## Documentation ownership and routing

Repository documentation follows one rule: **one governed fact has one canonical owner**. A non-owning document may summarize for its audience, specialize the fact within a narrower declared scope, link to the owner, or preserve historical evidence. It must not redefine the same current fact independently.

Route information to the smallest durable owner:

| Information | Canonical owner |
|---|---|
| Repository scope, agent operating rules, authority order, documentation routing, and parallel-change workflow | `AGENTS.md` |
| Trust assumptions and the semantic meaning of HR-001, HR-002, and HR-003 | `docs/TRUST-MODEL.md` |
| Current implemented product architecture, interfaces, boundaries, and implementation status | `SPEC.md` |
| Approved target/future architecture | `docs/PLATFORM-CONCEPT.md` |
| Machine-readable hard-rule declaration | `policy/kis-mcp.policy.json` |
| Installation, configuration, startup, commissioning, verification, troubleshooting, and recovery | `docs/OPERATIONS.md` |
| Human orientation, quick start, repository navigation, and links to canonical detail | `README.md` |
| Durable module-specific contracts and roadmaps | the applicable `docs/*-MODULE-PRODUCT-SPEC.md`, subordinate to the authority order above |
| One active change's scope, requirements, plan, execution state, and closeout evidence | `.work/changes/<change-id>/` |
| Specialist engineering evidence or historical development notes | `docs/development/**` |
| Reusable development procedures | canonical KIS Skills module catalogue; repository-local skill copies are prohibited |
| Executable settings, schemas, contracts, and policy values | the applicable JSON, contract, source, or test artifact |

Apply these rules when writing documentation:

1. Update an existing canonical owner instead of creating an overlapping document.
2. Keep `README.md` as a projection and index; link to architecture, policy, and operations rather than duplicating volatile detail.
3. Use root `SPEC.md` only for current product truth. Use a module product spec only for a long-lived scoped architectural domain, and state its parent/current-implementation authority where needed.
4. Use `.work/changes/<change-id>/spec.md` only for the bounded active change. After merge, the entire change record becomes historical evidence; reconcile durable outcomes into the canonical owner instead of continuously rewriting old `.work` records.
5. Do not create new active feature `spec.md` or `plan.md` files under `docs/development/**`; this repository's active change system is `.work/changes/<change-id>/`.
6. Supporting or historical documents must defer to the current authorities and must not be used to override them.
7. Machine-enforceable facts belong in machine-readable artifacts and tests. Prose explains or links to them; it must not maintain a competing executable value.
8. A new top-level `docs/*.md` file requires a distinct long-lived ownership domain. If an existing authority can own the information, update that authority instead.

## Skill authority and routing

Reusable skills MUST be discovered and loaded through the KIS Skills module. Agents must use the module operations (`search_skills`, `load_skill`, `search_skill_files`, and `read_skill_file`) rather than reading a skill package directly from the filesystem. The module owns access to the operator-approved shared catalogue configured by `settings/skills.settings.json`; its backing path is an implementation detail, not an alternate agent access path.

This repository MUST NOT track a repository-local skill catalogue or reusable skill package. Historical change records may mention former local paths as evidence, but those records do not authorize current skill loading.

Apply skills under these rules:

1. The authority order in this file overrides every skill instruction.
2. A skill loaded through the Skills module is procedural guidance only. It cannot authorize network access, writes, credentials, dependencies, publication, deployment, or any other mutation beyond authority already granted by the operator and repository.
3. Skill presence, metadata, recommendation, or absence cannot create a fourth Work hard rule or override an approved repository decision.
4. When a procedure references another skill, resolve that skill through the Skills module. If it is unavailable there, perform the bounded repository-authorized step directly and record the limitation instead of reading an alternate filesystem copy.
5. Host-specific or deployment-specific skill instructions apply only when the repository and operator separately authorize that exact activity.

For specification-slice development, load canonical skill ID `develop-code` through the Skills module for executable implementation and canonical skill ID `develop-docs` through the Skills module for authoritative documentation. For mixed work, use both procedures against the same approved change record and current verification evidence.

These procedures remain subordinate to `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, and the current implementation phase. They cannot expand the runtime, alter HR-001 through HR-003, or make an unapproved future capability current.

## Supporting lessons record

`docs/LESSONS-APPLICABILITY.md` maps consolidated prior-project recommendations to the current repository. Use it as a review and planning aid after reading the authority documents above. It is non-authoritative, cannot add a fourth prohibited outcome, and must distinguish current coverage, continuing evidence needs, future-phase adoption, advisory triggers, and rejected interpretations.

## Greenfield boundary

This repository contains only:

1. integration with the authoritative Desktop Commander MCP distribution;
2. a small FastMCP gateway and enforcement layer written for this project;
3. ordinary local development operations exposed through Desktop Commander's normal tool contracts;
4. tests proving the three policy outcomes;
5. minimal operational documentation and scripts.

Do not import SDK2 or another predecessor as a runtime dependency. SDK2 artifacts may be inspected as source material, but copied material must be reduced, renamed, and reconciled with this repository's authority before admission.

The operator has approved `docs/PLATFORM-CONCEPT.md` as the final product direction. That approval changes the documentation boundary only: the repository may define the future Discover, Govern, Work, evidence, provider, catalogue, profile, and workflow model in authoritative documents. Do not implement those future capabilities, add runtime dependencies, or claim them as current behavior without a separately approved implementation phase.

Do not add a custom replacement filesystem, custom replacement terminal, forked Desktop Commander, or duplicated provider implementation unless the operator explicitly changes the implementation boundary.

## Trust model

`kis-mcp` is a private, single-operator, directly supervised system. It is not designed for unattended or unsupervised implementation.

Desktop Commander remains the provider of ordinary filesystem, editing, search, process, testing, and local Git operations. FastMCP is the enforcement and forwarding boundary. Tool implementation and policy remain separate.

## The only three prohibited outcomes

FastMCP may block or transform a call only for one of these outcomes:

1. **HR-001 — write outside `C:\Projects`:** block any resolved direct or indirect write effect outside the approved project boundary.
2. **HR-002 — unrestricted external network through Work:** do not expose network-only Work tools; block network modes or calls whose resolved Work effect is external network access.
3. **HR-003 — permanent deletion:** transform delete-like intent into a recoverable move beneath `C:\Projects\.kis-mcp\quarantine`; block when safe quarantine is impossible.

Tool names, executables, broad capability, destructive-looking metadata, or absence from a curated list are not independent policy reasons.

## Narrow enforcement standard

FastMCP evaluates the complete concrete invocation and its proven resultant effects. A block or quarantine decision is valid only when the combined tool, arguments, modes, working directory, explicit targets, composed actions, and resolved effects positively establish HR-001, HR-002, or HR-003.

A prompt phrase, word, URL string, tool name, executable, command, flag, capability class, destructive appearance, possible misuse, incomplete prediction, or missing resolver is not independently sufficient to block.

If a prohibited effect cannot be specifically established, allow the invocation. Add a future narrow resolver only after a concrete violating combination is identified and covered by conformance tests.

Structural input failures must remain distinct from hard-rule violations. Network-only provider capabilities may be unexposed when every invocation necessarily violates HR-002; do not retain redundant content or URL blocks for capabilities that cannot reach the Work surface.

## Desktop Commander integration

- Use `@wonderwhy-er/desktop-commander` from its authoritative source.
- Pin the tested version in `settings/kis-mcp.settings.json`.
- Do not fork, vendor, or reimplement Desktop Commander without explicit operator approval.
- Keep provider-generated configuration, logs, cache, and runtime state under `C:\Projects\.kis-mcp\desktop-commander`.
- Preserve the provider's normal tool names and schemas except where a minimal compatibility transform is required by FastMCP.
- Keep provider-native security features enabled when they do not create a fourth project policy rule.

Installation may require external network access. It is an explicit operator-supervised bootstrap action outside the normal Work tool path. Normal Work execution must not silently install or update packages.

## FastMCP enforcement layer

Keep the enforcement layer small and auditable:

```text
Desktop Commander tool call
        |
        v
resolve invocation effects
        |
        v
apply HR-001 / HR-002 / HR-003
        |
        +-- allow ----------------------> forward unchanged
        +-- HR-001 or HR-002 ----------> corrective rejection
        +-- HR-003 --------------------> quarantine transform or rejection
```

Separate effect resolution from policy decisions. The policy decision core must not know provider-specific tool names. Provider-specific resolution belongs in a narrow adapter with tests for every supported mutating, network-capable, deletion-capable, and command-execution shape.

Terminal and process tools remain available through Desktop Commander's normal contracts. Resolve and block only concrete invocations whose intent or declared effect matches HR-001, HR-002, or HR-003; uncertainty, tool breadth, or lack of a specialized parser is not an independent reason to block.

## Parallel change workflow

Parallel agent count is not limited. Coordination is enforced through explicit change claims rather than a cap on agents or worktrees.

First classify the concrete effect. A governed repository change exists when version-controlled repository content is created, modified, moved, or otherwise changed. A supervised runtime/operator action that leaves repository authority unchanged does not require a branch, worktree, or pull request solely for process compliance; Work Management may still track that operational work. For tracked work, the configured Work Management backend is authoritative only for operational command facts such as priority, Ready/hold/defer state, scheduling, and execution claims. Repository change records, Git/GitHub, and provider-native verification remain authoritative for implementation and evidence facts.

For governed repository changes:

1. Start from a clean primary `main` worktree and choose one unused stable change ID in the form `NNN-kebab-case`.
2. Create the authoritative local change first with `pwsh -File scripts/change-workflow.ps1 new <change-id> --outcome <text> --owned <path> --complexity <configured-value>`, adding zero or more configured `--risk-trigger <trigger>` values plus scope/dependency arguments as required. `settings/change-governance.settings.json` is the machine-readable authority for current complexity values/definitions, risk-trigger definitions, required lifecycle artifacts, verification limits, and risk-scaled specialist reviews. GitHub Issue/Project linkage is optional metadata and may be supplied at intake or reconciled later.
3. Record base evidence before implementation. `new` always records the local base commit/tree and classifies any supplied or locally available remote-tracking evidence as `same_sha`, `tree_equivalent`, `content_divergence`, or `unavailable`; governance does not fetch the network.
4. Work only in `.work/worktrees/<change-id>` on branch `change/<change-id>`. When Work Management exists, preserve its command authority for operational intent while projecting authoritative change/Git/verification facts back into it; Work Management does not create or override repository change authority.
5. Scale lifecycle artifacts, verification limits, and specialist-review defaults from the exact complexity/risk classification declared in `settings/change-governance.settings.json`; every governed change retains `scope.json`, with the remaining required artifacts selected by that configuration. Risk triggers add their configured safeguards/reviews and never increase complexity by themselves.

Complexity is objective workload/coordination evidence, not risk. Use the definitions in `settings/change-governance.settings.json`; file count remains supporting evidence only and never the classifier. Reclassify only when discovery materially expands scope or coordination.

Newly created scopes use schema version 4 with `complexity` plus additive `risk_triggers` drawn from `settings/change-governance.settings.json`. Risk triggers are workflow/evidence requirements only and never become a fourth Work hard rule. Historical schema-version-1/2/3 scopes remain valid and retain their original compatibility rules; schema-version-3 records retain their recorded `risk_profile` only as historical compatibility data. Local change governance performs no GitHub or other network call.

Path claims are repository-relative exact paths or recursive paths ending in `/**`. `owned_paths` are exclusive. An overlap is permitted only when every overlapping claim uses `shared_paths` and coordination is explicit through a dependency or integration owner. Duplicate outcomes, branches, worktree paths, change IDs, and uncoordinated overlaps must fail before worktree creation.

Before publication, run `pwsh -File scripts/change-workflow.ps1 check` from the change worktree plus focused/affected verification selected for the current change. Pull requests to `main` run the canonical repository verification once on the exact GitHub head; do not repeat that full pass locally or in a metadata-only closeout transaction. Merge readiness requires provider-native GitHub Actions evidence for that exact head. After the branch is merged into its declared base, run `pwsh -File scripts/change-workflow.ps1 cleanup <change-id>` from the clean primary worktree. Cleanup must refuse dirty or unmerged worktrees and must never force branch deletion. For schema-version-3/4 changes, verified merge and branch/worktree cleanup establish historical closed state without a second repository commit solely to rewrite lifecycle status.

Manual worktree creation is an emergency exception only. Register the same change artifacts before the first implementation edit and run `change-workflow.ps1 validate` immediately.

## Repository standards

- Write only within `C:\Projects`.
- Never permanently delete repository artifacts; use recoverable quarantine.
- Keep temporary files under `C:\Projects\.kis-mcp\temp` or the repository `.temp` directory when one is explicitly needed.
- Keep configuration in JSON.
- Treat `.gitattributes` as the repository authority for tracked text line endings. KIS `write_file` and `edit_block` compatibility handling must honor Git's effective `text`/`eol` attributes; preserve explicit CRLF exceptions and binary paths instead of applying a blanket conversion.
- Keep modules focused and dependency direction simple.
- Do not commit secrets, tokens, machine-specific credentials, generated state, package caches, provider installation contents, or quarantine contents.
- Do not represent target behavior as implemented without fresh applicable tests.
- Keep documentation minimal; update an existing authority instead of adding overlapping documents.

## Verification

`scripts/verify.ps1` remains the canonical repository verification entry point. During development, run focused/affected checks only as needed; the normal pull-request workflow runs the canonical verifier once on the exact GitHub head after one locked environment synchronization. At minimum, the canonical pass verifies:

- JSON configuration parses;
- the policy contains exactly HR-001, HR-002, and HR-003;
- direct filesystem writes outside `C:\Projects` are rejected;
- local writes inside `C:\Projects` are allowed;
- explicit external-network modes are rejected;
- delete intent is transformed to quarantine;
- path normalization and boundary-prefix edge cases are covered;
- Desktop Commander is not vendored or forked in the repository;
- documentation and implementation status agree.

## Stop rule

Stop when the requested bounded outcome is complete, verification is current, contradictions are resolved, and remaining work is explicitly deferred rather than implied complete.
