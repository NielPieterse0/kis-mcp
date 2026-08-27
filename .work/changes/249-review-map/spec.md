# Change Specification: Review Map

- **Change ID**: `249-review-map`
- **Status**: Implemented, pre-merge verification complete
- **Risk Profile**: standard

## Outcome

Add deterministic source-bound Review Maps for exact KIS change evidence.

## Authority and scope

- Authoritative source: existing Discover `InspectChangeResponse` and its exact `ChangeIdentity.fingerprint`.
- Review Maps are navigation/evidence only and create no review, verification, merge-readiness, or mutation authority.
- Owned implementation: Discover review-map contracts, builder, tool registration/capability metadata, and focused tests.
- Dependencies: existing bounded `inspect_change` source resolution and fingerprint semantics.

## Requirements

- **REQ-001**: Build maps from the exact inspected source fingerprint; reject an explicitly supplied stale fingerprint.
- **REQ-002**: Produce deterministic bounded file sections, relationships, coverage/navigation data, and progress metadata.
- **REQ-003**: Report omitted files and relationship truncation explicitly and mark incomplete output.
- **REQ-004**: Preserve diagnostics/unknowns and never let Review Map output satisfy review, verification, merge-readiness, or mutation gates.
- **REQ-005**: Expose the feature as a read-only Discover capability without persistent Review Map state.

## Acceptance

1. Same source evidence produces stable ordered Review Map output with the exact source fingerprint.
2. Supplying a different expected fingerprint fails closed as stale source evidence.
3. File, section, and relationship bounds are deterministic; omitted evidence is explicit and marks the map incomplete.
4. The public operation is read-only and explicitly carries no review, verification, merge, or mutation authority.
5. Existing Discover behavior remains regression-clean.

## Risks and recovery

- Risk: a navigation artifact could be mistaken for decision authority. Mitigation: explicit `authority` and `gate_authority` fields plus read-only capability metadata.
- Risk: bounded maps could hide evidence. Mitigation: explicit omitted-file and omitted-relationship reporting with `truncated`/`incomplete` semantics.
- Recovery: remove the additive tool/contract implementation; existing `inspect_change` remains authoritative and unchanged.

## Out of scope

- Persistent reviewer progress state or generated Review Map files.
- Open Code Review repository state, skills, managed `AGENTS.md` content, or OCR dependencies.
- Any change to review, verification, Work Management, or merge authority.
