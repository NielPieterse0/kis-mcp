# GitHub Project Management Capability Documentation Plan

**Documentation level:** Complex. The work defines source-of-truth ownership, external-provider use, automation, CI, security boundaries, schemas, migration, and future public workflows.

**Decision supported:** Approve or revise the complete target solution before any GitHub Project or runtime implementation begins.

**Primary audiences:** Operator, future implementation agent, architecture reviewer, security reviewer, and PR reviewer.

**Goal:** Produce one machine-readable target specification for a GitHub-native operational project-management capability integrated with the 047 modular composition architecture.

**Authority hierarchy:** `AGENTS.md` → `docs/TRUST-MODEL.md` → `SPEC.md` → `docs/PLATFORM-CONCEPT.md` → Provider module specification → current change record.

**Canonical output:** `docs/development/github-project-management/README.md`.

**Boundaries:** Documentation only. No remote GitHub mutation, runtime implementation, policy change, credential work, or edit to 047-owned paths.

## Source inventory and adaptations

| Source | Use | Adaptation or conflict |
|---|---|---|
| Repository authority documents | Product, policy, platform, provider, and Work boundaries | Current authority remains unchanged |
| Change 047 spec and plan | Capability contribution and workflow composition seams | Runtime integration depends on 047 merge |
| Change 045 Git workflow spec | Local diff/readiness/cleanup responsibilities | Project automation integrates; does not replace |
| Official GitHub Projects docs | Views, fields, issues, automation, and APIs | Product facts require implementation-time revalidation |
| Official GitHub MCP server | Projects/issues/PR/Actions toolsets and scopes | Pinned current KIS release may require upgrade |
| GitHub ruleset docs | Free/private enforcement limits | Required gates need fallback evidence |
| Operator discussion | Record types, decisions, holds, intake, reviews, and consolidated view | Converted into normative requirements |
## Information architecture

The specification will define:

1. product decision and authority model;
2. scope and non-goals;
3. record taxonomy, fields, lifecycle, and views;
4. intake, specification, decisions, assumptions, holds, and traceability;
5. review-run evidence and finding extraction;
6. modular architecture and public workflows;
7. provider, configuration, automation, CLI, CI, and Git integration;
8. security, consistency, bootstrap, migration, and recovery;
9. stable normative requirements and acceptance scenarios;
10. delivery phases, modularity gates, risks, and open decisions.

## Traceable tasks

| Task | Target | Sources | Review gate | Verification | Recovery |
|---|---|---|---|---|---|
| T1 | Change scope and plan | AGENTS, skills, active claims | No overlap with 047-owned paths | Scope JSON parse and governance check | Revert change artifacts |
| T2 | Product and record model | Operator direction, GitHub Projects docs | One source of operational truth | Heading/ID and terminology review | Revise document |
| T3 | Review/evidence workflow | Platform concept, review discussions | Reports separated from extracted records | Contract and lifecycle review | Remove unsupported target claims |
| T4 | Modular architecture | 047 spec/plan, Provider spec, modularity rubric | Explicit contracts and dependency direction | Boundary review; no implementation claim | Re-slice future phases |
| T5 | CLI/CI/Git/config/security | Change 045, GitHub docs, Trust Model | Configurable without fourth HR rule | Requirement and contradiction scan | Disable or defer features |
| T6 | Final review and verification | All sources and final diff | No blocking finding | Markdown, JSON, links, diff, scope checks | Amend or revert branch |

## Review and verification

- Review source-to-section traceability and requirement completeness.
- Check normative statements for one actor, condition, and outcome.
- Check target-state statements do not claim implementation.
- Check GitHub Free plan limitations are explicit.
- Run JSON parsing, placeholder search, Markdown structure checks, `git diff --check`, and change-scope checks.
- Record stale 041/046 claim conflicts as an external verification limitation until 048 lands.

## Completion boundary

This documentation stage is complete when the target specification and change artifacts are current, reviewed, and committed on the isolated branch. Runtime implementation remains active/deferred and MUST start only after operator approval and reconciliation with merged 047.
