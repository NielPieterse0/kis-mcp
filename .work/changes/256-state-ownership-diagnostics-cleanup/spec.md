# Change Specification: State Ownership Diagnostics Cleanup

- **Change ID**: `256-state-ownership-diagnostics-cleanup`
- **Status**: Implemented
- **Complexity**: `medium`
- **Risk triggers**: `destructive`, `persistent_state`, `public_contract`

## Outcome

Add bounded operator diagnostics for canonical KIS state ownership and a recoverable, preview-first cleanup path for proven-stale reconstructible source state.

## Authority and scope

- Authority: `AGENTS.md`, `docs/TRUST-MODEL.md`, current state ownership contract, #550.
- Reuse `StateOwnershipClass`/canonical path semantics; do not introduce a second namespace model.
- Cleanup must preserve HR-003: no permanent deletion, quarantine only.
- Global authority/auth/cache, durable evidence, project/worktree authority and current source state are never cleanup candidates.

## Requirements

- **REQ-001**: Inventory canonical state namespaces with ownership, identity, age/provenance and conservative stale status without reading payload contents.
- **REQ-002**: Detect orphaned project/source identities for source-scoped state.
- **REQ-003**: Mark cleanup safe only for `reconstructible-cache` state of a registered project whose source identity is proven absent; unregistered-project state remains diagnosable but is not automatically cleanable.
- **REQ-004**: Preview cleanup without mutation; preview returns a short-lived token bound to the exact path identity, and apply requires that token while holding the repository change-admission lock through final eligibility and signed `QuarantineService` commit.
- **REQ-005**: Repeated apply after successful quarantine is an idempotent `already_quarantined` result.
- **REQ-006**: Expose bounded local tools for inventory and explicit cleanup; apply requires both an idempotency key and the prior preview token.
- **REQ-007**: Quarantine persists a signed, write-through operation intent before payload movement so interruption before final metadata can be reconciled without losing recoverability.

## Acceptance

1. Canonical namespaces are classified into the existing ownership vocabulary with identities and bounded metadata.
2. Unknown top-level roots are reported, not inferred into a canonical ownership class.
3. Stale registered-project source caches are safe to quarantine; current sources and unregistered-project caches are not cleanup candidates.
4. Authoritative, durable, shared-auth and global cache/install state cannot be selected for stale cleanup.
5. Preview has no filesystem effect; apply uses recoverable quarantine and can be replayed safely.
6. Focused tests, change governance, specialist review and exact-head GitHub verification pass before closeout.

## Risks and recovery

- Risk: false stale classification could move useful generated state. Mitigation: cleanup eligibility is restricted to reconstructible source cache whose project/source identity is absent from current registry/worktree evidence.
- Risk: cleanup resembles deletion. Mitigation: only `QuarantineService` is used; restore metadata and payload integrity remain authoritative.
- Recovery: restore the returned quarantine operation with the existing quarantine restore path.

## Out of scope

- Permanent deletion or quarantine retention pruning.
- Automatic cleanup without explicit apply.
- Removing durable evidence, project authority, shared authentication, provider installations or global caches.
- Inferring runtime-instance liveness from persisted directories alone.
