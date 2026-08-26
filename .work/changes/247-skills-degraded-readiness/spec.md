# Change Specification: Skills Degraded Readiness

- **Change ID**: `247-skills-degraded-readiness`
- **Status**: Approved
- **Development level**: Medium — bounded public readiness contract across Skills and health surfaces.

## Outcome

Make Skills catalogue initialization failure explicitly machine-observable while preserving fail-open ordinary Work behavior.

## Authority and scope

- `AGENTS.md` and issue #525 define the repository and Work authority.
- Existing Skills fail-open behavior remains authoritative: malformed optional catalogue entries must not prevent ordinary Work startup.
- Owned implementation is limited to Skills runtime status/contributions, health projection, focused tests, and this change record.

## Requirements

- **REQ-001**: Successful Skills initialization reports a machine-readable ready component state.
- **REQ-002**: Failed Skills initialization preserves the corrective `SkillsError` and reports a degraded component state without disabling ordinary Work.
- **REQ-003**: Capability discovery exposes one degraded Skills catalogue contribution when no active skill catalogue can be built.
- **REQ-004**: `kis_health.ready` retains its existing provider-installation meaning while `implementation_status` distinguishes Skills ready vs degraded state.
- **REQ-005**: No HR-001/HR-002/HR-003 semantics or provider readiness behavior changes.

## Acceptance

1. **Given** valid Skills sources, **when** the runtime composes, **then** Skills operations and contributions remain ready and health reports Skills ready.
2. **Given** malformed shared skill frontmatter, **when** Skills initialization fails, **then** ordinary server construction succeeds and Skills operations preserve the corrective error.
3. **Given** that degraded runtime, **when** capability status is queried, **then** a `skills.catalogue` contribution is present with degraded readiness and the failure code is visible in its summary.
4. **Given** that degraded runtime, **when** health is queried, **then** global `ready` remains unchanged while `implementation_status.skills` reports the degraded failure code.

## Risks and recovery

- Risk: degraded status could be attributed to the wrong runtime when several servers are constructed in one process.
- Mitigation: Skills status is an immutable value owned by each composed gateway; `kis_health` receives it through that gateway's instance-local closure rather than process-global state.
- Recovery: remove the instance-local health projection and degraded synthetic contribution; existing fail-open unavailable-service behavior remains intact.

## Out of scope

- Reworking atomic catalogue refresh semantics.
- Changing shared skill authoring or the already-restored `develop-docs` source.
- Treating Skills degradation as a provider failure or a new Work hard rule.
