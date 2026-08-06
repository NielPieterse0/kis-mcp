# Work Management Intake Implementation Plan

## Modularity decision

Measured repository evidence supports preserving the provider-neutral `work_management` boundary and the separate GitHub provider adapter. The new behavior remains in two cohesive files: immutable record contracts in `records.py`, and intake commands/results/backend protocol in `intake.py`. Provider mutation is deferred until these contracts are stable.

## Tasks

1. Add failing tests for typed records and governance metadata.
2. Implement immutable record detail contracts and normalized record envelope.
3. Add failing tests for low-friction intake, idempotency, and bounded outcomes.
4. Implement provider-neutral intake commands, results, and backend protocol.
5. Update package exports and architecture checks.
6. Reconcile programme P2 status and documentation impact.
7. Run scope check, focused tests, full verification, and findings-first review.
8. Record closeout, commit, push, and raise a pull request.

## Documentation impact

Reader-facing documentation impact is deferred because this slice is internal and not publicly composed. Programme authority and change closeout must be updated before merge. Post-merge reader documentation remains required when P2 is exposed through a provider or public workflow.
