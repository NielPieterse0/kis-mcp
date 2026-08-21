# Change Specification: GitHub Provenance Validation

- **Change ID**: `217-github-provenance-validation`
- **Status**: Approved for implementation
- **Development level**: Medium — cross-phase coordinator evidence contract with architecture/public-contract risk

## Outcome

Make GitHub issue/PR/SHA provenance machine-verifiable and fail closed before narrative status can become coordinator audit or merge evidence.

## Authority and scope

- Authoritative sources: `AGENTS.md`, GitHub issue `#413`, current coordinator contracts, `SPEC.md`
- Owned: `src/kis_mcp/workflows/coordinator/**`, `tests/workflows/coordinator/**`, `contracts/coordinator/**`, `SPEC.md`
- Shared/excluded/dependencies: none
- Live GitHub provider identity is authoritative; narrative status is untrusted input.

## Requirements

- **REQ-001**: Define a strict versioned GitHub provenance tuple containing repository, issue number, pull-request number, exact head SHA, and optional merge SHA.
- **REQ-002**: Validate any claimed tuple against independently observed provider identity before it can become trusted coordinator evidence.
- **REQ-003**: Fail closed with typed, visible mismatch evidence; rejected/quarantined provenance must not enter integration.
- **REQ-004**: Carry the verified immutable tuple through packet, handoff, reconciliation, exact-head verification, integration, delivery, and cleanup evidence.
- **REQ-005**: Concurrent aggregation may deduplicate exact tuple matches only; conflicting claims for the same PR or issue remain quarantined evidence.
- **REQ-006**: Preserve existing coordinator authority, fencing, exact-head Git checks, and Work Management semantics.

## Acceptance

1. Mismatched issue↔PR identity is rejected with typed provenance failure.
2. A stale claimed head SHA is rejected even when repository/issue/PR numbers match.
3. Reused PR numbers in narrative status cannot overwrite or alias a different verified tuple.
4. Concurrent aggregation accepts identical verified tuples deterministically and quarantines conflicts.
5. Accepted reconciliation and integration evidence preserve the exact verified tuple; delivery records the provider-observed merge SHA without rewriting the frozen head.
6. Coordinator schemas reject malformed provenance and focused regression tests pass.

## Risks and recovery

- Risk: broadening packet contracts could invalidate existing coordinator fixtures or permit caller-supplied evidence to masquerade as provider truth.
- Mitigation: introduce explicit claimed-versus-observed validation, schema constraints, and fail-closed reconciliation.
- Recovery: revert this isolated change; no data migration or destructive state transition is introduced.

## Out of scope

- Generic GitHub provider redesign or a new agent-status subsystem.
- Work Management lifecycle-policy changes.
- Changing merge authority or replacing existing exact-head GitHub Actions gates.