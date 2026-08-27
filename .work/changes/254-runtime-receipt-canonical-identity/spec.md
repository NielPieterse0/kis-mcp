# Change Specification: Runtime Receipt Canonical Identity

- **Change ID**: `254-runtime-receipt-canonical-identity`
- **Status**: Implemented
- **Risk Profile**: standard

## Outcome
Route correctness-sensitive runtime receipts and checkpoints through the canonical runtime-instance state namespace without trusting identity-ambiguous legacy roots.

## Authority and scope
- Repository authority: `AGENTS.md`.
- State authority: `contracts/state/state-ownership.contract.json` via `StateNamespaceResolver`.
- Work authority: GitHub issue #555 under #548/#491.
- Owned consumers: commissioning runtime, housekeeping runtime, and `kis-dev` post-land restart receipts.
- Provider/project integration evidence remains Slice D (#556).

## State inventory
- Commissioning checkpoints, executions, and receipts: `runtime-instance-specific`.
- Housekeeping status, preview/apply receipts, and failures: `runtime-instance-specific`.
- Post-land restart latest receipt, lock, and state-root fallback: `runtime-instance-specific` for `kis-dev`.
- Previous fixed roots: compatibility/recovery evidence only; retained and never selected as current authority.
- Shared authentication, project state, provider evidence, and unrelated workflow state are outside this slice.

## Requirements
- **REQ-001**: Runtime stores resolve through the existing canonical ownership contract; no second namespace model is introduced.
- **REQ-002**: Normalized runtime identity participates in commissioning and housekeeping state paths.
- **REQ-003**: Post-land restart state resolves to the canonical `kis-dev` runtime namespace while preserving worker ownership, restart, and fallback semantics.
- **REQ-004**: Identity-ambiguous legacy roots remain untouched and are not auto-read or migrated into current authority.
- **REQ-005**: Existing retry/idempotency, checkpoint freshness, stale-worker rejection, and receipt ownership semantics remain intact.

## Acceptance
1. `kis-op` and `kis-dev` resolve distinct runtime namespaces for the same state key.
2. Commissioning and housekeeping production composition uses those distinct roots.
3. Post-land restart uses `runtime/kis-dev/state/post-land-restart` and leaves the legacy receipt unchanged.
4. Focused runtime/state suites, changed-file lint, diff checks, governed scope checks, review, and exact-head CI pass.
5. Current-revision restart commissioning succeeds after merge before #555 completes.

## Risks and recovery
- Risk: a consumer could accidentally resume stale legacy runtime state. Mitigation: canonical-only production construction plus explicit legacy-retention tests.
- Risk: restart receipt relocation could weaken ownership ordering. Mitigation: retain the existing lock, landed SHA, worker PID, and atomic replacement behavior.
- Recovery: revert Change 254. Legacy evidence remains in place; canonical runtime files are recoverable state and must not be permanently deleted.

## Out of scope
- Shared/reusable authentication and vault state.
- Provider/project integration evidence owned by #556.
- State consumers already migrated by earlier #548 slices.
