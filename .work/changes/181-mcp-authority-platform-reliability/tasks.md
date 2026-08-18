# Tasks: MCP Authority and Platform Reliability

## Umbrella documentation

- [x] Confirm repository authority and exact upstream `main`.
- [x] Record official MCP schema/specification as protocol authority.
- [x] Define fail-closed MCP authority receipt requirement.
- [x] Record cross-repository execution-environment requirement; prohibit `doc-solution` special cases.
- [x] Record seven remediation slices.
- [x] Record mandatory sequential child-branch/PR landing rule.
- [ ] Validate umbrella change scope and documentation.
- [ ] Commit and publish umbrella documentation.
- [ ] Merge umbrella documentation before creating Slice 1.

## Slice 1 — MCP authority, source, and execution environment

- [ ] Create child change from exact merged `main`.
- [ ] Implement MCP protocol impact/authority receipt gate.
- [ ] Implement MCP Resources plus `InitializeResult.instructions` guidance.
- [ ] Implement canonical `ResolvedSource`.
- [ ] Implement generic product `ResolvedExecutionEnvironment` isolation.
- [ ] Add focused/conformance/regression tests.
- [ ] Complete exact-head review and verification.
- [ ] Merge, align local `main`, reconcile, and clean child branch/worktree.

## Slice 2 — Review orchestration v2

- [ ] Create only after Slice 1 is fully landed and reconciled.
- [ ] Implement provider-neutral backend health/fallback pool.
- [ ] Integrate issue #335 complete deterministic review batching.
- [ ] Add grounded review context and false-positive calibration.
- [ ] Add failure-domain and coverage tests.
- [ ] Complete exact-head review and verification.
- [ ] Merge, align local `main`, reconcile, and clean child branch/worktree.

## Slice 3 — Complete Work Management pagination

- [ ] Create only after Slice 2 is fully landed and reconciled.
- [ ] Implement page/cursor/completeness contract.
- [ ] Implement bounded authoritative auto-drain and typed incompleteness.
- [ ] Apply to inventory, selection, readiness, and exact lookup.
- [ ] Add multi-page/boundary regressions.
- [ ] Complete exact-head review and verification.
- [ ] Merge, align local `main`, reconcile, and clean child branch/worktree.

## Slice 4 — Durable PR and pre-merge readiness

- [ ] Create only after Slice 3 is fully landed and reconciled.
- [ ] Implement durable idempotent PR preparation stages and receipts.
- [ ] Implement stage deadlines and resume behavior.
- [ ] Implement authoritative Work Management pre-merge bootstrap/readiness.
- [ ] Add interruption/resume/readiness regressions.
- [ ] Complete exact-head review and verification.
- [ ] Merge, align local `main`, reconcile, and clean child branch/worktree.

## Slice 5 — Repository and Windows worktree lifecycle

- [ ] Create only after Slice 4 is fully landed and reconciled.
- [ ] Implement safe registered default-branch alignment.
- [ ] Remove governed worktrees from long-lived inherited CWD paths.
- [ ] Harden KIS-owned Windows process reaping and bounded handle retry.
- [ ] Add deterministic lock diagnostics and identity-guarded recovery.
- [ ] Add Windows lifecycle regressions.
- [ ] Complete exact-head review and verification.
- [ ] Merge, align local `main`, reconcile, and clean child branch/worktree.

## Slice 6 — Post-merge lifecycle reconciliation

- [ ] Create only after Slice 5 is fully landed and reconciled.
- [ ] Implement structured landing receipt/machine-owned closeout facts.
- [ ] Implement idempotent post-merge reconciliation.
- [ ] Reconcile stale change 179 through the new primitive.
- [ ] Integrate primitive with issue #325 housekeeping direction.
- [ ] Add idempotency/stale-record regressions.
- [ ] Complete exact-head review and verification.
- [ ] Merge, align local `main`, reconcile, and clean child branch/worktree.

## Slice 7 — Permanent acceptance matrix

- [ ] Create only after Slice 6 is fully landed and reconciled.
- [ ] Implement hermetic Small/Medium/Large execution matrix.
- [ ] Cover concurrent runs, distinct product environments, identity, containment, recovery, and receipt integrity.
- [ ] Regress deterministic contracts from Slices 1–6.
- [ ] Keep live-provider/product-repo commissioning separate from mandatory verification.
- [ ] Complete full exact-head canonical verification and required reviews.
- [ ] Merge, align local `main`, reconcile, and clean child branch/worktree.
- [ ] Reconcile and close umbrella programme.
