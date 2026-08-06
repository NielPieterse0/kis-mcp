# Change Specification: Multi-Project Work Management Foundation

- **Change ID**: `049-github-project-management-spec`
- **Status**: Active — P0 complete; backend integration deferred
- **Risk Profile**: standard
- **Development level**: Complex programme; bounded P0 implementation

## Outcome

Establish the long-lived work-management programme outside `docs` and implement the first provider-neutral domain foundation for multiple configured repositories.

GitHub remains the initial backend. P0 does not mutate GitHub, register gateway tools, or modify any path owned by active change 047.

## Authority and scope

- Authority: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, and the operator-approved programme direction.
- Working authority: `.work/programmes/work-management/target-spec.md`.
- Programme control: `.work/programmes/work-management/programme.json` and `roadmap.md`.
- Architecture decision: `.work/programmes/work-management/ADR-001-provider-neutral-domain.md`.
- Owned implementation: `src/kis_mcp/work_management/**`.
- Owned tests: `tests/work_management/**`.
- Dependency: active change 047 for later workflow and gateway composition.

## P0 requirements

- **REQ-001**: The domain MUST identify every managed repository through a stable project identity.
- **REQ-002**: Project identity MUST include project ID, local root, repository identity, and backend binding without importing provider code.
- **REQ-003**: Work records MUST identify their managed project and use validated record and lifecycle enums.
- **REQ-004**: Lifecycle transitions MUST be deterministic and reject undeclared transitions.
- **REQ-005**: `Done` MUST require a completed documentation milestone when documentation mode is required.
- **REQ-006**: Documentation impact MUST support `not_assessed`, `none`, `planned`, `in_progress`, `pre_merge_complete`, and `post_merge_complete`.
- **REQ-007**: Next-work selection MUST exclude blocked, held, deferred, rejected, superseded, and dependency-incomplete records.
- **REQ-008**: Next-work selection MUST be deterministic, project-filterable, and explain its exclusions and ordering.
- **REQ-009**: The P0 package MUST import no FastMCP, gateway, provider, workflow, or GitHub adapter module.
- **REQ-010**: P0 MUST create no remote records, persistent migration, credentials, or policy change.

## Acceptance

1. **Given** two managed projects, **when** records are selected, **then** each remains attributable to its project and optional project filtering is exact.
2. **Given** a record in a non-executable state or with incomplete dependencies, **when** next work is selected, **then** it is excluded with a stable reason.
3. **Given** documentation mode `required`, **when** a record attempts to transition to `Done` before post-merge reconciliation, **then** the transition is rejected.
4. **Given** documentation impact `none`, **when** reviewer evidence is recorded, **then** the documentation milestone may satisfy completion without document paths.
5. **Given** the active 047 restructuring, **when** scope and architecture checks run, **then** no 047-owned path or integration surface is modified.
6. **Given** the provider-neutral package, **when** imports are inspected, **then** no provider, workflow, gateway, FastMCP, or GitHub-specific dependency exists.

## Risks and recovery

- Risk: the domain becomes a catch-all for adapters and workflows.
- Mitigation: enforce the ADR and P0 architecture tests; defer adapter, workflow, settings, and automation modules.
- Risk: documentation status becomes an authorization rule.
- Mitigation: documentation mode controls delivery readiness only and never changes HR-001, HR-002, or HR-003.
- Risk: project identity is inferred from mutable current-directory state.
- Mitigation: require explicit project identity in domain records and commands.
- Recovery: revert the P0 package, tests, and programme artifacts before public integration. P0 creates no remote or migrated state.

## Out of scope

- GitHub Project inventory, creation, mutation, or commissioning.
- GitHub adapter, provider registration, workflow registration, gateway exposure, or public tools.
- Settings schema, CLI, CI, Actions, review evidence persistence, or reconciliation automation.
- Reader-facing README, operations, product, or module documentation updates before the programme reaches its configured documentation milestone.
- Changes to 040, 047, policy, or existing platform composition paths.
