# kis-mcp

Repository: `C:\Projects\kis-mcp`
Remote: `https://github.com/NielPieterse0/kis-mcp.git`

## Repository contract

- Product, distribution, and CLI: `kis-mcp`; import package: `kis_mcp`.
- Runtime settings: `settings/kis-mcp.settings.json`.
- Enforcement policy: `policy/kis-mcp.policy.json`.
- Generated state: `C:\Projects\.kis-mcp`, except the approved ignored agnix compatibility runtime under `.temp\tools\agnix`.
- This is a private, single-operator, directly supervised system.

## Authority order

Applicable authorities keep this precedence:

1. `AGENTS.md` — repository operating rules and documentation routing.
2. `docs/TRUST-MODEL.md` — trust assumptions and HR-001/HR-002/HR-003 semantics.
3. `SPEC.md` — current implemented product architecture and boundaries.
4. `docs/PLATFORM-CONCEPT.md` — approved target architecture only.
5. `policy/kis-mcp.policy.json` — machine-readable hard-rule declaration.
6. `docs/OPERATIONS.md` — canonical operator entry/routing; linked `docs/operations/**` runbooks hold scoped installation, startup, commissioning, verification, troubleshooting, and recovery procedures.

Read `AGENTS.md` and the active `.work/changes/<change-id>/` record for every governed repository change. Then load only the additional owners applicable to the task or affected paths. A lower authority never overrides a higher applicable authority.

| Change concern | Required additional context |
|---|---|
| Trust boundary, policy enforcement, HR semantics | `docs/TRUST-MODEL.md` and applicable policy/contracts/tests |
| Current product behavior or architecture | Relevant `SPEC.md` section and any durable module product spec |
| Target/future architecture or platform direction | `docs/PLATFORM-CONCEPT.md` |
| Installation, startup, deployment, commissioning, recovery, operator workflow | `docs/OPERATIONS.md` index plus only the linked `docs/operations/**` runbook needed for the task |
| Machine-enforceable value or interface | Applicable JSON, schema, contract, source, and tests |
| Historical decision or prior engineering evidence | `docs/development/**` only when investigation requires it |

Do not load a document merely because it mentions the feature. Do not use `README.md`, historical records, or target-state prose as implementation authority.

## Documentation ownership and routing

One governed fact has one canonical owner. Non-owning documents may summarize for their audience, specialize a narrower scope, link to the owner, or preserve historical evidence; they must not redefine current truth.

| Information | Canonical owner |
|---|---|
| Repository workflow, authority routing, path claims | `AGENTS.md` |
| Trust assumptions and HR semantics | `docs/TRUST-MODEL.md` |
| Current implemented product architecture/status | `SPEC.md` |
| Approved target architecture | `docs/PLATFORM-CONCEPT.md` |
| Machine-readable hard rules | `policy/kis-mcp.policy.json` |
| Operator procedure and live commissioning guidance | `docs/OPERATIONS.md` entry/index with scoped `docs/operations/**` runbooks |
| Human orientation/navigation | `README.md` |
| Durable module contract | applicable `docs/*-MODULE-PRODUCT-SPEC.md` |
| Active change scope, plan, tasks, evidence | `.work/changes/<change-id>/` |
| Historical/specialist engineering evidence | `docs/development/**` |
| Executable values and contracts | applicable JSON/schema/source/test artifact |
| Reusable procedures | canonical KIS Skills module catalogue |

A durable module product spec specializes only its declared module scope and remains subordinate to the ranked authorities above, including `SPEC.md` for current implementation truth. Resolve any conflict in favor of the earlier applicable authority.

Update the smallest existing canonical owner. A new top-level `docs/*.md` file requires a distinct long-lived ownership domain, and active feature `spec.md`/`plan.md` files belong under `.work/changes/<change-id>/`, not `docs/development/**`. After merge, a change record becomes historical evidence; promote only durable outcomes into their canonical owner.

## Skills

Reusable skills must be discovered and loaded through the KIS Skills module, never from a repository-local skill catalogue. This repository must not track a local skill catalogue or reusable skill package. Use the module operations `search_skills`, `load_skill`, `search_skill_files`, and `read_skill_file`; skill instructions are procedural guidance and remain subordinate to repository authority. A skill cannot expand operator- or repository-granted authority for writes, network access, credentials, dependencies, publication, deployment, or other external effects.

For governed implementation, load canonical `develop-code`. For governed documentation, load canonical `develop-docs`. Mixed changes use both against the same approved change record and current evidence. Skill presence, metadata, recommendation, or absence does not create authority or a fourth Work hard rule.

## Hard constraints

The Work policy has exactly three prohibited outcomes; authoritative semantics remain in `docs/TRUST-MODEL.md` and machine values in policy JSON:

- **HR-001:** no resolved write effect outside `C:\Projects`.
- **HR-002:** no resolved unrestricted external-network effect through Work.
- **HR-003:** delete-like intent becomes recoverable quarantine or is rejected.

Tool names, broad capability, uncertainty, appearance, profiles, readiness, or allow/deny lists do not create another Work rule. Do not weaken or reinterpret the three rules without explicit operator approval.

Current product boundaries, provider composition, Desktop Commander integration, and target evolution belong to `SPEC.md` and `docs/PLATFORM-CONCEPT.md`; do not duplicate them here.

## Governed repository changes

Parallel agent count is not limited. Coordination is enforced through explicit change claims and isolated worktrees.

A governed change exists when version-controlled repository content changes. Pure supervised runtime/operator actions that leave repository authority unchanged do not require a branch/worktree/PR solely for process compliance.

For a governed change:

1. Start from a clean primary `main` worktree aligned with verified GitHub default-branch truth.
2. Create one unused stable change ID in `NNN-kebab-case` form with `scripts/change-workflow.ps1 new`, declaring the outcome, a configured complexity value, additive risk triggers, owned/shared/excluded paths, and dependencies as applicable. `settings/change-governance.settings.json` owns the complexity values, classifications, risk triggers, and required lifecycle artifacts. Complexity measures workload/coordination, not risk; risk triggers add configured safeguards/reviews and never increase complexity. Reclassify only when discovery materially expands scope or coordination.
3. Record base evidence before implementation. Local governance does not fetch the network.
4. Work only in `.work/worktrees/<change-id>` on `change/<change-id>`.
5. Keep `scope.json` current. Path claims are exact repository-relative paths or recursive `/**` paths. `owned_paths` are exclusive; overlaps are permitted only when every overlap is explicitly shared and coordinated by dependency/integration ownership. Duplicate outcomes, change IDs, branches, worktree paths, or uncoordinated overlaps must fail before worktree creation.
6. Work Management may own operational priority, Ready/hold/defer state, scheduling, and execution claims. It does not create or override local change, Git, verification, or merge authority.
7. During development run only focused/affected checks needed for the change. Before publication run `pwsh -File scripts/change-workflow.ps1 check` from the change worktree.
8. Pull requests to `main` own the canonical full repository verification once on the exact GitHub head. Merge readiness requires provider-native GitHub Actions evidence for that exact head.
9. After verified merge, run `pwsh -File scripts/change-workflow.ps1 cleanup <change-id>` from clean primary `main`. Cleanup must refuse dirty or unmerged worktrees and must never force branch deletion. Historical schema-version-1/2/3 scopes remain valid under their compatibility rules; schema-version-3 `risk_profile` is historical data only. For schema-version-3/4 changes, verified merge plus cleanup establishes historical closed state without a second metadata-only repository commit.

Manual worktree creation is an emergency exception only. Register the same change artifacts before the first implementation edit and run `pwsh -File scripts/change-workflow.ps1 validate` immediately.

## Repository standards

- Write only within `C:\Projects`.
- Never permanently delete repository artifacts; use recoverable quarantine.
- Keep temporary/generated state under the configured KIS state root or approved ignored repository `.temp` locations.
- Keep configuration in JSON and executable facts in machine-readable artifacts/tests where practical.
- Treat `.gitattributes` as tracked text line-ending authority; preserve explicit CRLF and binary exceptions.
- Keep modules focused and dependency direction simple.
- Do not commit secrets, tokens, machine-specific credentials, caches, provider installations, generated state, or quarantine contents.
- Do not represent target behavior as implemented without fresh applicable evidence.
- Keep documentation minimal: link to canonical owners instead of maintaining parallel volatile truth.

## Verification and closeout

`scripts/verify.ps1` is the canonical repository verification entry point. The normal PR workflow runs it once on the exact GitHub head after locked environment synchronization. Local development should prefer focused checks unless a separate explicit canonical run is required.

Verification must continue to prove the three-rule set, repository/configuration integrity, provider and contract boundaries, current documentation/implementation consistency, and applicable change-governance requirements. Detailed verification and operator procedures belong to `docs/OPERATIONS.md`.

Close only when the requested bounded outcome is complete, current evidence supports the claims, blocking review findings are resolved, documentation reconciliation is complete where required, and remaining work is explicitly optional or out of scope.
