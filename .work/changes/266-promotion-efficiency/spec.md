# Change Specification: Promotion Efficiency

- **Change ID**: `266-promotion-efficiency`
- **Status**: Active
- **Risk Profile**: rigorous

## Outcome

Reduce normal PromotionReady-to-Done provider traffic and workflow ceremony by at least 20% without removing exact-head Actions, Work merge readiness, expected-head merge, landed reconciliation, Work/source closeout, or safe cleanup.

## Authority and scope

- Authoritative sources: Work #593, `SPEC.md`, PromotionReady/PromotionController contracts, registered GitHub exact operations.
- Owned paths: once-through promotion; project-management documentation reconciliation; documentation event model/tests; `SPEC.md`; Change 266 records.
- Dependencies: landed Change 265 crash-safety and terminal-receipt semantics.
- Integration owner: `codex-workflow-efficiency`.

## Requirements

- **REQ-001**: PR creation consumes title/context already carried by Work and performs no source-issue read on the happy path.
- **REQ-002**: Actions discovery binds one exact workflow run from one workflow-scoped page; retries poll that persisted run directly.
- **REQ-003**: registered branch reconciliation owns remote review-branch observation; promotion must not pre-read the same branch.
- **REQ-004**: landed inclusion uses exact equality first and otherwise a conclusive local ancestry assertion against the exact registered-refresh default revision; provider commit-history traversal is not used.
- **REQ-005**: an empty post-merge documentation update set completes in one external logical reconciliation call while retaining internal due→complete lifecycle semantics.
- **REQ-006**: matching PromotionReady evidence continues to suppress duplicate implementation verification/review before PR creation; canonical full verification remains exact-head GitHub Actions.

## Acceptance

1. A successful PR preparation path performs no source-issue metadata read and no pre-reconcile review-branch read.
2. Initial exact-head Actions discovery performs one workflow-scoped list read; pending retries perform only direct reads of the bound run.
3. The normal provider/tool-boundary call budget falls from approximately 17 calls to 13, a 23.5% reduction, without removing a distinct safety gate.
4. Worst-case workflow history listing falls from up to ten 100-run pages to one 100-run page; persisted retries perform zero list calls.
5. Landed inclusion performs no provider commit-history scan: exact merge/default equality is the fast path, otherwise local `git merge-base --is-ancestor` proves the relationship against the exact refreshed default SHA.
6. No-op documentation reconciliation accepts an empty update set and reaches `post_merge_complete` in one tool invocation.
7. Focused regression suites and governed scope validation pass before publication; canonical full verification runs once in GitHub Actions on the exact PR head.

## Risks and recovery

- Risk: removing redundant reads could hide provider drift. Mitigation: retain exact identity validation at the operation that owns each mutation/evidence boundary.
- Risk: empty documentation updates could bypass lifecycle rules. Mitigation: internally apply the due event before the completed event; only the external ceremony is collapsed.
- Recovery: revert Change 266; Change 265 durable resume semantics remain unchanged.

## Out of scope

- Removing substantive review, exact-head Actions, Work merge readiness, merge expected-head guards, terminal receipts, or safe cleanup.
- Replacing P0 checkpoint durability solely to reduce the visible count of persisted stages.
