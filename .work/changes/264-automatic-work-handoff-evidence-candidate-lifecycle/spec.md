# Change Specification: Automatic Work Handoff Evidence Candidate Lifecycle

- **Change ID**: `264-automatic-work-handoff-evidence-candidate-lifecycle`
- **Status**: Active
- **Work**: `WORK-586` / GitHub issue `#586`
- **Complexity**: `large`
- **Risk triggers**: `architecture_boundary`, `external_action`, `persistent_state`, `public_contract`

## Outcome

Make once-through handoff, evidence continuity, permanent candidate identity, and exact-process lifecycle automatic at successful Work activation, with deterministic idempotent re-entry.

## Authority and scope

- `AGENTS.md` governs repository workflow and closeout.
- `SPEC.md` owns current implemented product behavior.
- GitHub issue `#586` owns the requested Work outcome and acceptance criteria.
- `scope.json` owns the exact change path claims and Work linkage.
- Existing once-through contracts/evidence validity classes remain authoritative; this change extends their lifecycle rather than defining a parallel model.

## Requirements

- **REQ-001**: Successful `Ready -> Active` claim/take automatically materializes one immutable task handoff from the source issue.
- **REQ-002**: Candidate port allocation is atomic with first handoff persistence, permanent for the Work identity, and never reused for another Work identity.
- **REQ-003**: Retry/parallel activation reuses the exact contract and port; changed contract content fails closed.
- **REQ-004**: Evidence is durably appended by immutable evidence ID and preserves selective validity-class semantics.
- **REQ-005**: Implementation/review, live candidate, provider exact-head, merge, and post-merge receipts share one evidence lineage by reference.
- **REQ-006**: Candidate runtime receipts bind Work, contract fingerprint, source identity, actual source path, PID, and server-instance identity; a matching live candidate is reused.
- **REQ-007**: Candidate shutdown targets only the exact recorded PID/instance after matching live proof is durably persisted; unrelated occupants are never terminated.
- **REQ-008**: Promotion uses the candidate's persisted governed source path and PromotionReady change identity without mutating the immutable Work-origin contract.

## Acceptance

1. Apply-claim and apply-take create the task handoff only after the Active transition is proven successful.
2. Parallel/repeated materialization yields one contract fingerprint and one candidate port for the Work identity.
3. Evidence append is idempotent for identical content and rejects mutation behind an existing evidence ID.
4. Live candidate verification persists runtime-sensitive evidence before candidate cleanup can proceed.
5. Exact-process cleanup refuses owner mismatch or missing durable live evidence.
6. Provider exact-head, merge, landed, documentation, and Work completion receipts extend the durable evidence lineage.
7. Promotion remains resumable while source checkout identity comes from the persisted candidate receipt and change identity comes from PromotionReady.
8. Focused tests, change-governance check, specialist review, and canonical repository verification pass before publication.

## Risks and recovery

- A failed Work transition must not create a handoff; the activation gate checks successful outcomes before materialization.
- A stale/unrelated process on the assigned port must never be killed; endpoint identity and exact PID/instance ownership are mandatory.
- Evidence writes are atomic and use unique temporary paths; immutable evidence IDs reject divergent replay.
- Recovery is idempotent re-entry from persisted contract/evidence/candidate/promotion state. No destructive state reset is required.

## Out of scope

- Typed obligation schema redesign and broader default PromotionReady reuse planned by later programme slices.
- New MCP protocol primitives or changes to the three Work hard rules.
