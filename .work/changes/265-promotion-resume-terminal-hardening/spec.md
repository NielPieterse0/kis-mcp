# Change Specification: Promotion Resume Terminal Hardening

- **Change ID**: `265-promotion-resume-terminal-hardening`
- **Status**: Active
- **Risk Profile**: rigorous
- **Source Work**: `WORK-592` / issue #592

## Outcome

Make PromotionReady-to-Done reuse authoritative external identities across retries, reconcile uncertain side effects from provider truth, prevent ambiguous half-applied Work/source closeout, and persist one durable terminal delivery receipt.

## Authority and scope

- `AGENTS.md`, `SPEC.md`, Work #592, and the immutable Work handoff are authoritative.
- Owned implementation is limited by `scope.json`.
- Change 264 already owns automatic Work handoff, evidence lineage, permanent candidate identity, reuse, and exact-owner candidate cleanup; this change must not duplicate those primitives.
- Existing substantive implementation review, exact-head GitHub Actions, Work merge readiness, exact-head merge, landed reconciliation, documentation completion, and safe cleanup gates remain mandatory.

## Requirements

- **REQ-001 — Persisted Actions identity:** once one exact PR/head Actions run is qualified, a blocked/pending retry MUST poll that persisted run ID directly rather than rescan branch workflow history.
- **REQ-002 — Authoritative invalidation:** a persisted Actions identity MUST remain bound to the exact PR/head and fail closed if provider truth no longer proves that association.
- **REQ-003 — Merge uncertainty:** if the exact-head merge mutation loses its response, the workflow MUST reread authoritative PR truth before attempting another merge mutation.
- **REQ-004 — Half-applied closeout:** if Work completion succeeds but source issue closure fails, the completed Work result MUST be checkpointed and retry MUST resume source closure without repeating Work completion.
- **REQ-005 — Identity preflight:** scope Work/project/repository/change identity MUST agree with the immutable handoff before promotion side effects begin.
- **REQ-006 — Terminal receipt:** successful cleanup MUST produce one durable `promotion-terminal-receipt-v1` binding Work/change/source, PR/head, Actions run, merge, landed revision, documentation completion, Work/source closeout, and cleanup evidence.
- **REQ-007 — Done replay:** replay of the same fully completed promotion MUST return the existing terminal receipt without provider mutation, review, verification, or stage replay.
- **REQ-008 — Post-land safety:** existing restart cleanliness and landed/launch identity protections MUST remain green, including empty-clean, generated-evidence-only, unrelated-dirt, and launched-SHA cases.

## Acceptance

1. A pending exact-head Actions run is discovered once; retry performs no workflow-history listing and reads the persisted run directly.
2. Lost merge response with provider-observed merged PR returns the exact merge identity without a second merge mutation.
3. Lost/failed source close after successful Work completion returns a resumable blocked observation; retry closes the source without another Work-completion call.
4. Mismatched scope Work identity is rejected before any promotion stage executes.
5. Completion persists the terminal receipt in the PromotionController checkpoint; a second identical convergence call performs no stage invocation and returns the same receipt.
6. No PromotionReady path invokes a substantive implementation review or a second local canonical full repository verification.
7. The full once-through regression suite and post-land restart regression suite pass on the implementation tree.
8. Change-governance scope and static syntax/whitespace checks pass.

## Risks and recovery

- Persisted provider identities can become stale. Recovery is authoritative invalidation/fail-closed behavior, never silent rebinding to a different head/run.
- A provider mutation can succeed while its response is lost. Recovery is authoritative provider reread before another mutation.
- Terminal receipt schema becomes durable audit evidence; changes must remain backward-readable or be versioned explicitly.
- Rollback is ordinary Git revert of this bounded change; existing Change 264 handoff/evidence primitives remain independent.

## Out of scope

- Removing or weakening substantive review, exact-head CI, Work merge readiness, exact-head merge guards, landed truth, documentation completion, or cleanup.
- P1 provider-call optimisations such as source-issue metadata reuse, documentation no-op collapse, or replacing landed commit-history scans.
- P2 workflow telemetry, audit UI/surface, board truncation/query semantics, or generated human-readable historical closeout views.
