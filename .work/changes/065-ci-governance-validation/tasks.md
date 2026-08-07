# Tasks: CI Governance Validation

- [x] Confirm authority, failure evidence, and bounded scope.
- [x] Add a failing regression for isolated validation while preserving strict local validation.
- [x] Implement explicit `validate --claims-only` behavior and opt Work Management CI into it.
- [x] Run focused governance/workflow tests: 23 passed.
- [x] Run `scripts/change-workflow.ps1 check` and `git diff --check`.
- [x] Run canonical `scripts/verify.ps1`: passed.
- [ ] Commit, push, review, and merge the exact verified head.
- [ ] Reconcile PR #80 onto repaired main and rerun its exact-head Windows gate.
- [ ] Close and safely clean change 065 after integration.
