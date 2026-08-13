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
| Reusable development procedures | `.agents/skills/**` |
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

Repository-local skills under `.agents/skills` are procedural development aids. They are not product, runtime, policy, or repository authority, and their presence does not prove that a platform capability is implemented. The runtime Skills module is separate: it resolves the operator-approved shared catalogue at `C:\Projects\.agents\skills` through `settings/skills.settings.json`. Shared runtime skills remain reusable procedures rather than repository-specific authority; ChatGPT loads their instructions and executes resulting work through the ordinary kis-mcp Work surface.

Apply skills under these rules:

1. The authority order in this file overrides every skill instruction.
2. An externally adopted skill is authorized only when its directory contains an `adoption-manifest.json` whose approval status is `approved`. Use it only within the capabilities, filesystem scope, activation mode, dependencies, and risk boundary recorded by that manifest.
3. A skill without an approved adoption manifest is reference-only guidance. It may inform MVP development, but it must not impose gates, require external access, authorize mutations, add dependencies, create a fourth policy rule, or override an approved repository decision.
4. A skill requirement to invoke another skill applies only when that referenced skill is authorized under this section. Otherwise perform the necessary bounded step directly under repository authority and record any resulting verification limitation.
5. Skill instructions that assume another host, deployment model, network access, package installation, publication, directory submission, or remote service are inapplicable unless the operator separately approves that exact activity.

The following repository-owned workflow skills are explicitly authorized by this file for specification-slice development, even though they are not third-party adopted skills:

- Use `.agents/skills/develop-code/SKILL.md` for an approved specification slice that creates, changes, fixes, refactors, or verifies executable implementation. It coordinates the slice from requirements through planning, implementation, review, verification, and closeout without changing the approved product boundary.
- Use `.agents/skills/develop-docs/SKILL.md` for a documentation-only specification slice or an authoritative documentation update. It coordinates sources, authority, structure, review, verification, and closeout without turning target-state documentation into an implementation claim.
- For a mixed slice, use `develop-code` for executable changes and `develop-docs` for authoritative documentation, then reconcile both against the same approved specification and current verification evidence.

These workflow skills remain subordinate to `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, and the current implementation phase. They cannot expand the runtime, alter HR-001 through HR-003, or make an unapproved future capability current.

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

Before implementation begins:

1. Start from a clean primary `main` worktree and choose one unused stable change ID in the form `NNN-kebab-case`.
2. Create the authoritative local change first with `pwsh -File scripts/change-workflow.ps1 new <change-id> --outcome <text> --owned <path> --risk-profile <lean|standard|rigorous>`, adding scope/dependency arguments as required. GitHub Issue/Project linkage is optional projection metadata and may be supplied at intake or reconciled later.
3. Record base evidence before implementation. `new` always records the local base commit/tree and classifies any supplied or locally available remote-tracking evidence as `same_sha`, `tree_equivalent`, `content_divergence`, or `unavailable`; governance does not fetch the network.
4. Work only in `.work/worktrees/<change-id>` on branch `change/<change-id>`. Keep any Work Management projection synchronized when one exists, but do not treat it as change authority.
5. Keep lifecycle artifacts scaled to the recorded risk profile: `lean` uses `scope.json` plus `change.md`; `standard` and `rigorous` use `scope.json`, `spec.md`, `plan.md`, `tasks.md`, and `closeout.md`. Risk changes must be recorded rather than compensated for with duplicate evidence files.

Newly created scopes use schema version 3. Historical schema-version-1/2 scopes remain valid and retain their original compatibility rules; schema-version-2 records continue to require their recorded Work Management initialization evidence. Local change governance performs no GitHub or other network call.

Path claims are repository-relative exact paths or recursive paths ending in `/**`. `owned_paths` are exclusive. An overlap is permitted only when every overlapping claim uses `shared_paths` and coordination is explicit through a dependency or integration owner. Duplicate outcomes, branches, worktree paths, change IDs, and uncoordinated overlaps must fail before worktree creation.

Before publication, run `pwsh -File scripts/change-workflow.ps1 check` from the change worktree plus focused/affected verification selected for the current change. Pull requests to `main` run the canonical repository verification once on the exact GitHub head; do not repeat that full pass locally or in a metadata-only closeout transaction. Merge readiness requires provider-native GitHub Actions evidence for that exact head. After the branch is merged into its declared base, run `pwsh -File scripts/change-workflow.ps1 cleanup <change-id>` from the clean primary worktree. Cleanup must refuse dirty or unmerged worktrees and must never force branch deletion. For schema-version-3 changes, verified merge and branch/worktree cleanup establish historical closed state without a second repository commit solely to rewrite lifecycle status.

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
