# Tasks: GitHub Provenance Validation

- [x] Confirm issue #413 authority, Work Management readiness, clean/aligned `main`, and governed Change 217 scope.
- [x] Define Medium-level specification and implementation plan.
- [x] Add failing regression tests for issue↔PR mismatch, stale head, reused narrative PR identity, concurrent aggregation, and immutable lifecycle propagation.
- [x] Implement strict GitHub provenance contract and provider-resolution admission.
- [x] Propagate verified provenance through worker handoff, reconciliation, integration, CI, delivery, and cleanup evidence.
- [x] Update JSON schemas and `SPEC.md`.
- [x] Run focused coordinator tests and schema validation.
- [x] Run `pwsh -File scripts/change-workflow.ps1 check`.
- [x] Complete required architecture/API-contract/code-quality review and resolve findings; final automated retries exhausted reviewer deadlines, so the configured manual exact-diff fallback was used and recorded in closeout.
- [ ] Prepare exact-head PR; require canonical Actions and Work Management merge-readiness.
- [ ] Merge only approved head, reconcile documentation/Work Management, refresh `main`, and governed cleanup.