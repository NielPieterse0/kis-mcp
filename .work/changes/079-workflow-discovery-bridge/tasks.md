# Tasks: Workflow Discovery Bridge

- [x] Confirm authority, active claims, and isolated scope.
- [x] Batch 1: implement bounded read-only `plan_change` with active-claim evidence.
- [x] Batch 1: run focused tests, scope check, review, and canonical verification.
- [x] Batch 1: create PR #87, pass exact-head Work Management run #22, merge, and reconcile 079.
- [ ] Batch 2: implement `run_verification`, workflow integrity, recommendation, and CI triage.
  - [x] Implement and register the `run_verification` execution bridge and `verification-result-v1`.
  - [x] Implement conflict-free workflow specs, exact-head CI classes, executable-step integrity helper, and deterministic workflow matcher.
  - [ ] Integrate central workflow descriptors/resolvability/recommendation after active change 063 releases those exclusive paths.
- [x] Batch 2 core: PR #89 / Work Management #25 merged `run_verification`.
- [x] Batch 3 primitives: PR #90 / Work Management #26 merged conflict-free workflow integration helpers.
- [ ] Final shared adapter: dependency 063 is now closed; claim released catalogue/resolver/workflow paths, integrate, verify, and merge.
- [ ] Record final closeout evidence and clean 079 from merged `main`.
