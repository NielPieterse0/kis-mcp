# Change Specification: Review Candidate Identity

- **Change ID**: `610-review-candidate-identity`
- **Status**: Implemented
- **Risk Profile**: standard

## Outcome

Complete #587 by automating validated implementation-review closure, exact candidate reuse identity, and deterministic effect-aware candidate scenario selection.

## Authority and scope

- Authorities: `AGENTS.md`, issue #587, issue #587/#588 coordination comments, existing once-through contracts.
- Owned: `review.py`, `candidate_runtime.py`, `process_identity.py`, focused #587 test file, this change record.
- Shared: `once_through/tools.py`, coordinated with Change 612 / #588 before edit.
- Excluded: #588 contracts/promotion/evidence/state paths and `src/kis_mcp/skills/**`.
- Integration owner: `610-review-candidate-identity` for the narrow #587 `tools.py` integration.

## Requirements

- **REQ-001**: Derive `ReviewClosure` only from completed substantive reviews with no open material finding.
- **REQ-002**: Compute correction re-review domains only from finding closure/correction delta/directly affected paths.
- **REQ-003**: Candidate v2 identity binds Work, contract, server instance, source commit/tree, policy/runtime fingerprints, endpoint, and OS process identity.
- **REQ-004**: Reuse only the exact live v2 candidate; mismatched occupants or drift fail closed.
- **REQ-005**: Derive deterministic live scenarios from affected surfaces/tools, preserving read/effect boundaries and negative paths.

## Acceptance

1. Closed reviews emit `review_closed` evidence; material findings block closure.
2. A correction touching one finding path selects only its affected review domain.
3. Exact v2 identity reuses; source/tree/policy/runtime/endpoint drift rejects reuse or promotion.
4. Automatic scenarios are stable regardless caller ordering and never execute effectful tools without explicit approval.

## Risks and recovery

- Risk: stale pre-v2 candidate receipts cannot prove the expanded identity.
- Recovery: legacy receipts remain stoppable but are not reusable; restart creates v2 identity.

## Out of scope

- #588 typed obligation/promotion/evidence/state changes and #569 skills work.
