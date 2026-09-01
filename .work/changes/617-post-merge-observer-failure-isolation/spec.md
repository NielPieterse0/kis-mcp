# Change Specification: Post-Merge Observer Failure Isolation

- **Change ID**: `617-post-merge-observer-failure-isolation`
- **Status**: Active
- **Complexity**: medium
- **Risk triggers**: `external_action`, `persistent_state`

## Outcome

A retryable failure in one historical commissioning merge candidate no longer prevents independently valid later candidates from being observed, while any unresolved candidate still prevents checkpoint advancement.

## Authority and scope

- Authorities: `AGENTS.md`, relevant `SPEC.md` commissioning architecture, `docs/OPERATIONS.md`, and `docs/operations/post-merge-commissioning.md`.
- Owned implementation: `src/kis_mcp/commissioning_runtime/service.py`.
- Owned tests: `tests/post_merge_commissioning/test_runtime_service.py`.
- Owned operator documentation: `docs/operations/post-merge-commissioning.md`.
- Source issue: #620; execution owner: `agent-c`.

## Requirements

- **REQ-001**: Isolate retryable candidate-processing exceptions to the exact PR candidate and continue the bounded scan.
- **REQ-002**: Persist bounded typed unresolved-candidate evidence without provider exception detail.
- **REQ-003**: Preserve the previous checkpoint whenever any discovered candidate remains unresolved.
- **REQ-004**: Preserve whole-scan failure semantics for candidate discovery/search-envelope failures and shared budget exhaustion.
- **REQ-005**: Do not weaken merge/source/change identity, immutable `blocked_evidence`, or the no-self-restart rule.

## Acceptance

1. Given PR #565-style retryable merge evidence failure followed by a valid later candidate, both produce per-candidate outcomes in the same scan.
2. The unresolved candidate is typed and bounded; provider detail is absent from the receipt.
3. The scan remains incomplete and the checkpoint remains unchanged until all candidates are accounted.
4. Existing successful, immutable blocked-evidence, discovery-failure, budget, corruption, scheduler-hosting, and freshness behaviors remain covered.

## Risks and recovery

- Risk: treating a whole-scan resource failure as candidate-local could create noisy repeated failures. Mitigation: budget exhaustion is explicitly re-raised to the whole-scan boundary.
- Risk: advancing past unresolved history would lose evidence. Mitigation: any candidate-local failure returns an incomplete run before checkpoint advancement.
- Recovery: remove the isolated exception handling to restore prior fail-fast behavior; persisted receipts/checkpoints remain compatible.

## Out of scope

- Reclassifying immutable landed-governance failures.
- Historical backfill or manual checkpoint rewriting.
- MCP-extension/Skills telemetry work owned separately from #620.
- Any `kis-op` self-restart behavior.
