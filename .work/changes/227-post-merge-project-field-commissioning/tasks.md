# Tasks: Post-Merge Project Field Commissioning

- [x] Confirm current design, live schema drift, #409 ownership, and absence of an existing merged-PR commissioning observer.
- [x] Define field-only boundary without weakening full-schema atomic preflight.
- [x] Add failing provider tests for scoped field commissioning and preflight safety.
- [x] Implement shared field preflight/apply/verify helpers and fields-only path.
- [x] Extend existing registered operation with fixed `full|fields` scope contract.
- [x] Add registered-operation and capability-contract regression tests.
- [x] Reconcile `SPEC.md`.
- [x] Run focused tests, `git diff --check`, and `change-workflow.ps1 check`.
- [x] Run required code-quality, architecture, API-contract, and test-quality review.
- [x] Run canonical repository verification.
- [ ] Commit and publish exact-head PR; require exact-head GitHub Actions and Work merge-readiness.
- [ ] Merge, reconcile documentation/Work state, and clean Change 227.
- [ ] Refresh runtime, invoke live `scope=fields`, and record #419 field commissioning evidence.