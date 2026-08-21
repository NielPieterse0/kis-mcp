# Closeout: Work Management Canonical Contracts

## Current phase

Implementation complete; final verification/review/delivery is in progress.

- Change 226 remains bound to `WORK-430` from base `3c46f0b275ba2471c6b84268c6360d9d8e0ddf15`.
- The operator approved `spec.md` and `plan.md` on 2026-08-21 before implementation began.
- Three Work-specific canonical contracts now own item/vocabulary/applicability, lifecycle/operation, and selection semantics.
- Command-plane settings, runtime vocabulary, lifecycle guards, both selection adapters, and the GitHub Project field projection consume or exact-validate against those contracts.
- The generic Work `automation` object is removed; housekeeping remains the explicit scheduler/receipt/apply authority.
- The Project projection now contains the three #419 live-verification fields as its final managed fields.
- `project_management_contract` exposes normalized canonical contracts and fingerprints through the existing read-only MCP surface.
- No #444/Change 223 work-class tier and no generic MRD framework were introduced. No live GitHub Project schema mutation was performed.

## Verification evidence

- Focused canonical, lifecycle, command-plane, selector, schema, settings, onboarding, and housekeeping suites pass.
- The bounded Work/onboarding/housekeeping suite passes with the workflow CLI test excluded only because of the independently reproducible clean-main workflow-package circular import.
- That circular import was reproduced unchanged on clean `main`; it is not treated as a Change 226 regression.
- `git diff --check` passes and changed tracked files use the repository line-ending policy.
- `pwsh -NoProfile -File scripts/change-workflow.ps1 check` passes.
- Full repository verification passed on the final implementation state with `pwsh -NoProfile -File scripts/verify.ps1 -SkipDependencySync`: pytest exit code `0`, repository line endings/configuration/interpreter/dependencies/Python syntax/change-governance checks all passed, and the verifier reported `verification.ok=true`.

## Review evidence

- Final architecture, API-contract, and test-quality automated review attempts each returned `AGENT_REVIEW_FAILED:EvidenceError`; none is counted as an automated pass.
- The required manual exact-diff fallback reviewed the canonical loader/model, all three canonical contracts, lifecycle guard migration, both selection adapters/shared ranker, command-plane/provider projection validation, obsolete automation removal, #419 field projection, MCP contract exposure, and the new drift/regression tests.
- The manual fallback found no blocking Change 226 finding, no #444 work-class/tier logic, no live Project mutation path, and no deliberate selection-order change. Full canonical verification then passed on the reviewed implementation state.
- `governance-audit.md` records rule ownership, automation disposition, semantic completeness limits, provider projection boundaries, and the independent baseline import defect.

## Residual items

- Commit and publish through the governed PR path; require canonical GitHub Actions on the exact PR head.
- Merge only when exact-head Work/GitHub readiness permits, then perform post-merge Work/documentation reconciliation and governed cleanup.
- Hand live Project schema repair and runtime contract proof to #419 using the exact merge SHA and current schema-status evidence.