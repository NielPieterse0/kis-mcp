# Change Specification: Provider Commissioning Evidence

- **Change ID**: `126-provider-commissioning-evidence`
- **Status**: Implementation complete; landing and live commissioning authorized by SPEC-136 / issue #197
- **Complexity**: `medium`
- **Risk triggers**: `persistent_state`, `public_contract`

## Outcome

Persist bounded historical commissioning evidence for DBHub and Docker Hub so a KIS restart preserves prior verified integration status while current-process runtime evidence remains separate.

## Authority and scope

- Current provider behavior: `SPEC.md` plus the DBHub and Docker Hub provider modules.
- Operator commissioning procedure: `docs/OPERATIONS.md` and `scripts/commission-db-docker-providers.ps1`.
- Generated evidence root: derive `commissioning/providers` from JSON-owned `paths.state_root`.
- Defect source: issue #143 / `BUG-143`.
- Implementation/landing authority: issue #197 / `SPEC-136`.

## Requirements

- **REQ-001**: Successful commissioning writes deterministic bounded evidence beneath the configured KIS state root.
- **REQ-002**: Evidence applies only to the exact provider, configuration, binding, and tool identity that was verified.
- **REQ-003**: Provider readiness distinguishes historical commissioning from current-process runtime state.
- **REQ-004**: Repeated commissioning for unchanged identity is idempotent.
- **REQ-005**: DBHub and Docker Hub tests cover commission, reconstructed readiness, and stale evidence rejection.
- **REQ-006**: Provider availability, authentication semantics, enabled tool surfaces, and the three Work hard rules remain unchanged.

## Acceptance

1. After successful DBHub commissioning, a new readiness instance with identical identity reports historical commissioning as verified instead of never-commissioned/pending-only.
2. Docker Hub behaves equivalently in public mode.
3. Changing provider revision, configuration identity, or DBHub binding identity makes prior evidence inapplicable.
4. Current-process readiness/mount state remains separately observable and is not inferred from historical evidence.
5. Existing provider surface tests remain green.

## Risks and recovery

- Risk: stale evidence could overstate integration readiness if identity matching is incomplete.
- Mitigation: hash a normalized exact identity and validate the stored document before use.
- Recovery: evidence is derived generated state; remove or quarantine the applicable evidence outside normal runtime and rerun commissioning.

## Out of scope

- Persisting process-lifetime OAuth state.
- Changing Docker Hub search exposure.
- Changing provider installation or routing configuration.
