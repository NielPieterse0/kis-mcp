# Multi-Project Work Management Foundation Plan

**Development level:** Complex programme with a bounded standard-risk P0 change unit. The programme crosses provider, workflow, CI, and persistent operational boundaries, but P0 changes one new provider-neutral package and creates no remote state.

**Approved outcome:** Relocate working authority into `.work/programmes`, generalize it across managed repositories, add documentation feedback milestones, and implement the P0 domain foundation.

**Architecture:** Immutable domain contracts and pure lifecycle/selection functions. Provider, workflow, gateway, settings, persistence, and GitHub integration remain later units.

**Tech stack:** Python 3.11+, dataclasses, enums, pathlib, pytest, repository verification.

## Global constraints

- Stay inside `scope.json`.
- Do not modify active 047 paths.
- Use failing tests before production behavior.
- Add no runtime dependency.
- Keep the domain independent of FastMCP and external providers.
- Create no remote GitHub state.
- Keep documentation milestones separate from HR policy.

## Requirement traceability

| Task | Requirements | Evidence |
|---|---|---|
| T1 Programme relocation and generalization | REQ-001, REQ-010 | Programme JSON, target spec, roadmap, scope check |
| T2 Project and record contracts | REQ-001, REQ-002, REQ-003, REQ-006 | Failing then passing contract tests |
| T3 Lifecycle and documentation milestone | REQ-004, REQ-005, REQ-006 | Transition tests including required documentation failures |
| T4 Next-work selection | REQ-007, REQ-008 | Deterministic filtering, ordering, and explanation tests |
| T5 Architecture and completion review | REQ-009, REQ-010 | Import-boundary test, diff review, full verification |

## Task 1: Programme authority

- Move the complete target specification from `docs/development` to `.work/programmes/work-management/target-spec.md`.
- Add `programme.json`, `roadmap.md`, modularity evidence, and ADR-001.
- Generalize hard-coded repository assumptions into managed-project and backend-binding contracts.
- Add pre-merge and post-merge documentation milestone requirements.

## Task 2: Domain contracts — TDD unit 1

- Write failing tests for project identity, record identity, record types, lifecycle state, and documentation impact.
- Implement `contracts.py` and package exports only.
- Run the focused contract tests and fast repository verification.

## Task 3: Lifecycle — TDD unit 2

- Write failing tests for allowed transitions and documentation completion prerequisites.
- Implement pure lifecycle validation with bounded structured failures.
- Run focused lifecycle tests and fast verification.

## Task 4: Next-work selection — TDD unit 3

- Write failing tests for state, dependency, approval, project, priority, and stable-order filtering.
- Implement pure selection returning the selected record and per-record reasons.
- Run focused selection tests and fast verification.

## Task 5: Review and verification

- Add an architecture test proving P0 imports no provider, workflow, gateway, FastMCP, or GitHub adapter package.
- Review specification-to-test traceability, edge cases, error semantics, modular boundaries, and scope.
- Run `git diff --check` and `scripts/change-workflow.ps1 check`.
- Run focused tests and `pwsh -NoProfile -File scripts/verify.ps1`.
- Record residual work as later programme phases rather than claiming full capability completion.

## Documentation feedback milestone

P0 documentation impact is `planned`. The working programme artifacts are updated in this change. Reader-facing repository documents remain deferred because P0 is not publicly composed or commissioned. Before final programme integration, the delivery workflow must update README, operations, product/module specifications, and final implementation status, then record post-merge reconciliation before `Done`.

## Recovery

All P0 behavior is additive and unexposed. Revert the change commits to remove the package and tests. The programme artifacts remain recoverable through Git history. No remote rollback is required.
