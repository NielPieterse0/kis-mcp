# Change Specification: Workflow Terminal Audit

- **Change ID**: `267-workflow-terminal-audit`
- **Status**: Active
- **Complexity**: Large
- **Risk triggers**: `architecture_boundary`, `persistent_state`, `public_contract`

## Outcome

Make terminal workflow evidence canonical, typed, self-auditing, queryable, and efficiency-regression aware without creating a competing post-merge repository authority.

## Requirements

- **REQ-001**: Extend the durable promotion terminal receipt with generated closeout projection and persisted workflow telemetry, including stage timing/attempts, replay/block reasons, provider reads/mutations, page scans, verification/review attempts, and duplicate-attempt indicators.
- **REQ-002**: Expose a bounded read-only audit over recent terminal receipts that reports exact Work/change/source/PR/Actions/merge/landed/documentation/source-close/cleanup/restart identities and flags workflow-efficiency regressions.
- **REQ-003**: Validate Work handoff, source issue, record type, and typed Work record identity before promotion provider activity.
- **REQ-004**: Propagate targeted Work-board query semantics to the GitHub Project provider before `item_limit` so known records cannot disappear solely because an unrelated page exhausted the bound.
- **REQ-005**: Preserve implementation review ownership: promotion consumes established review/verification evidence and audit distinguishes legitimate specialist lanes from duplicate attempts.
- **REQ-006**: Record explicit implementation-source to reconciled-PR-head verification lineage when the revisions differ.

## Acceptance

1. A completed promotion is inspectable from one bounded read-only audit surface and includes exact terminal delivery identities plus generated closeout state.
2. Done replay performs no external lifecycle mutation and increments durable replay telemetry.
3. Targeted Project lookup is filtered by the provider before the caller item bound.
4. Typed Work/specification mismatch fails before provider mutation/read choreography begins.
5. Regression coverage preserves the once-through lifecycle and review-ownership model.

## Recovery and boundaries

Tracked change Markdown remains historical/pre-merge evidence after landing. Terminal delivery truth comes from the durable receipt and provider/Work evidence; no metadata-only post-merge repository commit is required. Rollback is ordinary change revert plus removal of the new audit surface/telemetry fields; existing terminal receipt readers remain tolerant of absent telemetry on historical receipts.