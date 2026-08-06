# Change Specification: GitHub Project Management Capability

- **Change ID**: `049-github-project-management-spec`
- **Status**: Active — documentation baseline
- **Risk Profile**: rigorous
- **Documentation level**: Complex

## Outcome

Define the complete target-state requirements, modular boundaries, lifecycle, evidence model, GitHub Project configuration, review extraction, CLI, CI, Git workflow, security, recovery, and phased delivery plan for a GitHub-native project-management capability in `kis-mcp`.

This change is documentation-only. It reserves an isolated worktree for future delivery but does not implement, configure, authenticate, or mutate GitHub Projects.

## Authority and scope

- Authority: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, `docs/PROVIDER-MODULE-PRODUCT-SPEC.md`, and the operator-approved direction in this workstream.
- Target specification: `docs/development/github-project-management/README.md`.
- Owned paths: this change record and the target specification directory.
- Excluded paths: policy, current product authority, gateway, capability composition, provider composition, and active changes 040/047/048.
- Dependencies: 047 for runtime composition; 048 for stale-claim reconciliation.
- Integration owner: deferred to a post-047 implementation slice.

## Requirements

- **REQ-001**: Preserve GitHub as the authoritative code, artifact, PR, CI, and implementation-history platform.
- **REQ-002**: Use one GitHub Project as the consolidated operational programme view.
- **REQ-003**: Define first-class ideas, work, specification slices, reviews, findings, decisions, assumptions, risks, approvals, holds, and deferments.
- **REQ-004**: Define immutable traceability from idea through specification, change, PR, verification, merge, and closeout.
- **REQ-005**: Define a normalized review-run and evidence-extraction workflow.
- **REQ-006**: Define provider-neutral modular contracts compatible with the 047 platform composition architecture.
- **REQ-007**: Define configurable feature, automation, and gate modes without adding a fourth Work policy rule.
- **REQ-008**: Define complete CLI, CI, Git workflow, security, reliability, migration, recovery, and acceptance requirements.
- **REQ-009**: Distinguish GitHub Free capabilities from optional paid enforcement features.
- **REQ-010**: Leave runtime implementation, GitHub Project mutation, and commissioning out of this documentation slice.
## Acceptance

1. **Given** the current repository authority and 047 architecture, **when** the specification is reviewed, **then** the proposed capability has explicit module boundaries and dependency direction without claiming implementation.
2. **Given** the required project-management use cases, **when** the record model is inspected, **then** intake, delivery, decisions, assumptions, risks, approvals, holds, reviews, findings, and historical traceability are covered.
3. **Given** adjustable workflow requirements, **when** the configuration model is inspected, **then** features, automation, and gates can be independently disabled, advisory, or required where applicable.
4. **Given** GitHub Free plan limitations, **when** CI and branch controls are described, **then** unavailable enforcement is capability-detected and residual risk is explicit.
5. **Given** future implementation phases, **when** the delivery sequence is inspected, **then** each phase is separately bounded, verifiable, reversible, and preceded by current modularity evidence.
6. **Given** the active 047 restructuring, **when** this change diff is checked, **then** no 047-owned runtime or top-level authority path is modified.

## Risks and recovery

- Risk: the specification could hard-code a GitHub product detail that changes before implementation.
- Mitigation: identify external facts, record their verification date, and require revalidation against the pinned provider release.
- Risk: the project-management domain could become a catch-all module.
- Mitigation: define provider, domain, workflow, reconciliation, and evidence boundaries; require phase-level modularity assessment.
- Risk: the operational Project could compete with repository authority.
- Mitigation: store status, summaries, and immutable links only; keep full artifacts in Git.
- Recovery: revert or revise this documentation branch. No runtime, remote Project, or credential state is changed by this slice.

## Out of scope

- Runtime code, tests, JSON schemas, Actions workflows, issue forms, or project bootstrap.
- GitHub Project creation or mutation.
- Provider installation, upgrade, authentication, or scope changes.
- Changes to 047, 048, 040, policy, or current product authority.
- Pull-request creation, merge, or worktree cleanup for this reserved active change.
