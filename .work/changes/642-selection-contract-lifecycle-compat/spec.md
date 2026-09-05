# Change Specification: Selection Contract Lifecycle Compat

- **Change ID**: `642-selection-contract-lifecycle-compat`
- **Status**: Ready for verification
- **Risk Profile**: standard

## Outcome

Restore higher-level Work lifecycle compatibility with the canonical evolved work-selection contract while preserving tier semantics.

## Authority and scope

- Authoritative sources: canonical Work selection and lifecycle contracts under `settings/work-management/contracts`.
- Owned implementation: canonical contract projection and Work management service inventory selection.
- Regression coverage: command-service lifecycle and next-work behavior.
- Dependencies: none; linked Work item `WORK-696` / issue #696.

## Requirements

- **REQ-001**: Exact-target lifecycle commands must not require fields that exist only to rank/classify next-work candidates.
- **REQ-002**: Next-work must continue requesting every field declared by the canonical selection contract plus lifecycle readiness prerequisites.
- **REQ-003**: Claim, transition, completion, bounded exact-target resolution, and fail-closed behavior remain unchanged.

## Acceptance

1. **Given** the evolved selection contract, **when** exact-target lifecycle commands read one issue, **then** selection-only fields are not required.
2. **Given** next-work selection, **when** the canonical selection contract evolves, **then** all canonical selection field names are requested without duplicating the schema in service code.
3. **Given** claim, transition, and completion flows, **when** exercised after the change, **then** their existing state and fail-closed semantics remain intact.

## Risks and recovery

- Risk: over-pruning fields needed by readiness or completion.
- Mitigation: selection inventory composes lifecycle readiness fields with canonical selection fields; completion explicitly requests its delivery-stage field.
- Recovery: revert the bounded service projection change.

## Out of scope

- Changing selection tier ordering or ranking.
- Changing provider schema or project fields.
