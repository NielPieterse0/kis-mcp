# Change Specification: Work Management Intake

- **Change ID**: `052-work-management-intake`
- **Status**: Active
- **Risk Profile**: standard
- **Development level**: Medium

## Outcome

Implement P2 provider-neutral typed intake and first-class governance records for ideas, tasks, specification slices, decisions, assumptions, risks, approvals, holds, research, defects, findings, and review runs. Define bounded idempotent mutation contracts without exposing provider-specific transport or public gateway tools.

## Authority and scope

- Authoritative sources: `AGENTS.md` and `.work/programmes/work-management/target-spec.md`.
- Dependency: completed P1 change `051-github-project-inventory`.
- Owned paths are declared in `scope.json`.
- GitHub-specific mutation and live commissioning remain outside this slice.

## Requirements

- **REQ-001**: Define immutable typed record details with stable project and record identities.
- **REQ-002**: Decisions, assumptions, risks, approvals, and holds must have explicit required metadata.
- **REQ-003**: Holds and deferments must require a review trigger.
- **REQ-004**: Intake must accept low-friction idea capture without implementation metadata.
- **REQ-005**: Mutating commands must require an idempotency key and return explicit created, updated, conflict, or rejected outcomes.
- **REQ-006**: Provider-neutral contracts must not import FastMCP, gateway, workflow, or GitHub modules.
- **REQ-007**: No remote mutation or public workflow is introduced in this slice.

## Acceptance

1. **Given** a title and project ID, **when** an idea is captured, **then** a normalized Inbox record is produced without owner, estimate, or due date.
2. **Given** governance-specific metadata, **when** a decision, assumption, risk, approval, or hold is constructed, **then** required fields are validated deterministically.
3. **Given** a repeated idempotency key, **when** intake is executed, **then** the backend can return an update or conflict without creating an ambiguous duplicate.
4. **Given** the package source, **when** architecture checks run, **then** provider and platform imports are absent.

## Risks and recovery

- Risk: record-specific metadata creates an over-general catch-all type.
- Mitigation: use small immutable detail contracts and one normalized record envelope.
- Recovery: revert additive files and shared exports; no remote state is created.

## Out of scope

- GitHub issue or Project writes.
- Public gateway composition.
- Traceability, review evidence, CLI, CI, or Project provisioning.
