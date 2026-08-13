# GitHub Workflow Simplification Implementation Plan

**Development level:** Complex. Requirements and trade-offs are already operator-approved, so implementation proceeds without another design-approval loop.

**Architecture:** Keep repository-local change records and KIS exact-Git invariants authoritative. Make GitHub Issues/Projects/Actions projections and evidence providers. Scale local ceremony by risk and let exact-head CI own the single final full verification result.

**Efficiency rule:** Run focused tests for each tranche. Do not rerun the same full verifier locally after exact-head GitHub CI establishes the final result.

### Task 1 — Simplify change governance first

- Extend the change claim with an executable risk profile and local/remote base evidence.
- Make Work Management linkage optional projection metadata for new records while preserving schema-v1/v2 compatibility.
- Generate risk-scaled artifacts: lean = `scope.json` + `change.md`; standard/rigorous = current full record, with rigorous evidence requirements applied by workflow gates rather than duplicate files.
- Add focused governance tests first, then implementation.
- Restart `kis-dev` after this tranche so subsequent work uses the simplified initialization rules.

### Task 2 — Make CI exact-head and single-pass

- Trigger the canonical workflow on pull requests.
- Remove duplicate environment/test preparation before the full verifier.
- Pin Actions by immutable SHA.
- Expose/consume exact-head check-run/Actions evidence in completion flow.
