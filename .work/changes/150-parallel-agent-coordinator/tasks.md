# Tasks: Parallel Agent Coordinator — Slice 6 (#252)

## Prerequisites

- [x] #247 architecture/contracts landed.
- [x] #248 atomic reservation admission landed.
- [x] #249 scope revision/lease/fence authority landed.
- [x] #250 planner/runtime binding/work packets landed.
- [x] #251 durable worker lifecycle/MCP adapter landed via PR #328 at merge `6a5e843341f4213080014e5bd7388e8b1959baa9`.
- [x] Parent worktree fast-forwarded to current `main` after #251 landing.
- [x] Current repository local exact-head verification authority from change 179 applied to #252 design.

## Slice 6 implementation

- [x] Add deterministic reconciliation service and tests.
- [x] Validate assignment/reservation/fence/runtime/execution/task identity.
- [x] Validate independent exact-base/head/changed-path Git evidence.
- [x] Revalidate global claims plus local packet scope.
- [x] Block unsatisfied dependencies.
- [x] Consume assignment key atomically on accepted handoff; reject stale/revoked/consumed keys.
- [x] Derive verification checks/reviews from authoritative scope + configured change controls.
- [x] Replace stale provider-native verification contract semantics with KIS-local exact-head authority.
- [x] Add durable serialized integration queue and exact-head local-verification delivery gate.
- [x] Keep actual GitHub mutation in existing registered KIS operations.
- [x] Harden Windows lock initialization and mutation-receipt contention after full-regression failures; stress the two race scenarios 10/10 clean.

## Slice 6 gates

- [x] Focused reconciliation/integration tests pass.
- [x] Full coordinator regression suite passes after fixing the two surfaced Windows contention races.
- [x] Strict coordinator schemas validate Slice 6 emitted values.
- [x] Ruff and Python compilation pass on coordinator source/tests.
- [x] Governed change check and `git diff --check` pass.
- [ ] Required code-quality, architecture, API-contract, and persistent-state reviews have no blocking findings.
- [ ] Canonical KIS-local exact-head repository verification passes on the current PR head.

## Landing gate

- [ ] Freeze/reconcile Slice 6 with current `main` without widening scope.
- [ ] Publish/update the parent coordinator PR at the exact reviewed head.
- [ ] Run canonical local verification on that exact head and retain a concrete evidence reference.
- [ ] Merge only that head, refresh registered/local `main`, record #252 delivery, then begin #253.
