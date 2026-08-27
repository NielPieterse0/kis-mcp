# Change Specification: Reviewer Ensemble

- **Change ID**: `250-reviewer-ensemble`
- **Status**: Approved for implementation
- **Risk Profile**: rigorous

## Outcome

Add bounded independent reviewer ensembles and optional adjudication while KIS remains the sole review-evidence, verification, and merge authority.

## Authority and scope

- Authoritative source identity remains the exact fingerprint returned by verification selection / source inspection.
- Existing `review_change_with_agent` remains the only reviewer execution primitive; ensemble orchestration adds no mutation or nested-agent authority.
- Existing single-reviewer behavior remains the default when no ensemble configuration is supplied.
- Owned implementation is limited to change-execution contracts, service/tool surface, focused tests, and this change record.

## Requirements

- **REQ-001**: Accept at most four explicit reviewer profiles with stable reviewer IDs and valid backend/model combinations.
- **REQ-002**: Execute each configured reviewer independently against the exact same source selector and fingerprint.
- **REQ-003**: Retain reviewer ID, backend/model, review type, source fingerprint, and candidate finding provenance.
- **REQ-004**: Deterministically deduplicate/corroborate candidate findings without deleting dissent or changing candidate cardinality silently.
- **REQ-005**: Bound reviewers, rounds, aggregate deadline, and total review invocations; malformed, stale, incomplete, timed-out, or over-budget outcomes fail closed.
- **REQ-006**: Optional adjudication requests are reported explicitly as requested/invoked/completed telemetry; until an adjudicator actually runs, dissent remains unresolved and no verification, merge-readiness, or mutation authority is implied.
- **REQ-007**: Emit bounded ensemble telemetry for unique findings, duplicates, rejected/error outcomes, disagreement, latency, and invocation count.
- **REQ-008**: Preserve the existing single-reviewer public behavior when ensemble options are absent.

## Acceptance

1. Multiple reviewer profiles inspect one exact source fingerprint without mutation authority.
2. Independent findings retain reviewer/model/source provenance.
3. Duplicate/corroborated findings remain traceable to every originating reviewer.
4. Optional adjudication requests preserve unresolved dissent and report requested/invoked/completed state without implying adjudication occurred.
5. Reviewer count, round count, invocation count, and deadline are deterministically bounded.
6. Existing single-reviewer calls return the existing result contract shape unless ensemble mode is requested.
7. Ensemble results never directly authorize verification or merge readiness.

## Risks and recovery

- Risk: orchestration could amplify provider cost or accidentally convert advisory consensus into authority. Mitigation: hard bounds, exact fingerprint checks, explicit no-authority metadata, and fail-closed aggregation.
- Recovery: remove the opt-in ensemble parameters/aggregation; the pre-existing single-reviewer execution path remains intact.

## Out of scope

- New reviewer providers or provider authentication.
- Persistent reviewer conversation state.
- Any change to Work Management, verification, or merge authority.
