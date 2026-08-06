# Change Specification: Work Management Traceability

- **Change ID**: `053-work-management-traceability`
- **Status**: Active
- **Risk Profile**: standard
- **Development level**: Medium

## Outcome

Implement P3 provider-neutral implementation traceability and documentation milestones for governed specification slices without adding provider mutation, public gateway composition, CLI, CI, or review-evidence behavior.

## Authority and scope

- Authoritative sources: `AGENTS.md` and `.work/programmes/work-management/target-spec.md`.
- Dependency: completed P2 change `052-work-management-intake`.
- Owned and shared paths are declared in `scope.json`; change `040-context7-serena-adapters` remains untouched.
- The provider-neutral package must not import FastMCP, gateway, workflow, or provider modules.

## Requirements

- **REQ-001**: Define immutable provider-neutral evidence contracts for specification ownership, change identity, branch, worktree, pull request, verification, merge, closeout, and documentation reconciliation.
- **REQ-002**: Preserve multiple pull requests and verification runs while keeping each evidence item independently serializable and queryable.
- **REQ-003**: Detect missing, stale, duplicated, and contradictory relationships with deterministic structured findings.
- **REQ-004**: Evaluate merge readiness against the exact pull-request head revision and require passing verification for that revision.
- **REQ-005**: Require pre-merge documentation completion or an explicit reviewed no-impact decision according to the configured documentation mode.
- **REQ-006**: Create a `documentation_reconciliation_due` event after merge that records project, change, pull request, merge commit, documentation task, and required post-merge updates.
- **REQ-007**: Prevent a traceability-required record from reaching `Done` until post-merge documentation reconciliation is recorded.
- **REQ-008**: Keep GitHub adaptation, remote mutation, public workflow exposure, review evidence, reconciliation automation, CLI, and CI outside this slice.

## Acceptance

1. **Given** a governed change, **when** traceability is evaluated at review, merge-ready, merged, or closed stage, **then** required evidence and relationship defects are reported deterministically.
2. **Given** duplicate or contradictory PR, merge, verification, or documentation evidence, **when** validation runs, **then** structured findings identify the defect and subject.
3. **Given** verification for an older revision, **when** merge readiness is evaluated, **then** readiness fails as stale evidence.
4. **Given** required documentation impact that is not pre-merge complete, **when** merge readiness is evaluated, **then** readiness fails without creating an HR policy decision.
5. **Given** a merged pull request, **when** the documentation milestone is applied, **then** the work record enters `Documentation` with `documentation_reconciliation_due`.
6. **Given** a traceability-required record with a due milestone, **when** `Done` is requested, **then** lifecycle transition is rejected until a completed reconciliation event is applied.
7. **Given** the package source, **when** architecture checks run, **then** the domain remains provider-neutral and bounded.

## Risks and recovery

- Risk: an over-general graph model obscures required workflow semantics.
- Mitigation: use explicit immutable evidence contracts and one cohesive traceability aggregate.
- Risk: documentation state duplicates lifecycle state.
- Mitigation: keep the milestone as evidence-specific state and retain `Documentation` as the lifecycle state.
- Recovery: revert additive contracts and narrow shared-file changes through Git; no remote records or migrations are created.

## Out of scope

- GitHub Project, issue, pull-request, or Actions mutations.
- Public capability composition or workflow descriptors.
- P4 review-run evidence and finding extraction.
- P5 reconciliation service, CLI, CI, automation, and portfolio status.
