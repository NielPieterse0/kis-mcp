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
- [x] Configured code-quality, architecture, and API-contract reviews plus persistent-state/trust-boundary fallback review have no blocking findings; the review engine required exact-diff fallback because its evidence package omitted the large reconciliation test file. One stale accepted-replay authority finding was fixed in `7aa6c23` and regression-tested.
- [x] Canonical KIS-local exact-head repository verification passed on `3196590e675abc916cc94e0f1638aef435ac2973`. The first full verifier run had one unrelated Discover inventory-race failure; that exact test then passed 5/5 on prior `main` and 5/5 on the #252 candidate with the canonical interpreter, and the fresh full verifier rerun passed completely.

## Landing gate

- [x] Freeze/reconcile Slice 6 with prior `main` without widening scope; exact candidate `3196590e675abc916cc94e0f1638aef435ac2973` descended from `6a5e843341f4213080014e5bd7388e8b1959baa9`.
- [x] Publish exact source/review branches as far as GitHub availability allowed; PR creation was independently blocked by GitHub HTTP 503 and is retained as remote-sync debt rather than a local landing gate under the operator-approved local-main recovery mode.
- [x] Run canonical local verification on exact candidate `3196590e675abc916cc94e0f1638aef435ac2973` and retain the passing verifier output in the execution transcript/change closeout.
- [x] Fast-forward local `main` only to that exact verified head. #252 repository delivery is complete locally; #253 remains the next slice after this closeout record is reconciled.
