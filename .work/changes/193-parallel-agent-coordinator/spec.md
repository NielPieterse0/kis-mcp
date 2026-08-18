# Change Specification: Parallel Agent Coordinator

- **Change ID**: `193-parallel-agent-coordinator`
- **Status**: Active reconstruction
- **Complexity**: `large`
- **Risk triggers**: `architecture_boundary`, `persistent_state`, `public_contract`

## Outcome

Reimplement the retained KIS parallel-agent coordinator from historical Change 150 through final head `4aae9dd30ad3536a84f5a08f805ae149116773e9`: contracts, authority state, deterministic planning, durable worker lifecycle, reconciliation, and serialized integration. Exclude the crisis-era Actions-loss local/VM verification-runner coupling.

## Authority and scope

- Repository authority: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, and `docs/PLATFORM-CONCEPT.md`.
- Reconstruction authority: issue #363 plus historical Change 150 / PRs #328 and #337.
- Current landing authority: provider-native GitHub Actions on the exact frozen pull-request head, followed by exact-head merge.
- Owned implementation is limited to coordinator contracts/runtime/tests/module spec and this change record.
- Reservation, scope-revision, lease, and fence state remain the coordinator mutation-authority plane.
- Runtime/MCP discovery remains advisory; worker completion is distinct from repository delivery.
## Requirements

- **REQ-193-01**: Restore the strict coordinator contract catalogue and typed models without widening public scope.
- **REQ-193-02**: Preserve deterministic reservation admission and revision/lease/fence authority, including stale/revoked/consumed rejection.
- **REQ-193-03**: Preserve deterministic dependency planning, conflict detection, serial integration ownership, and bounded work packets/runtime bindings.
- **REQ-193-04**: Preserve restart-safe worker execution, immutable invocation snapshots, bounded results, idempotent mutation handling, and ephemeral MCP worker adaptation.
- **REQ-193-05**: Reconciliation MUST validate packet, assignment, reservation/fence, runtime, execution/task identity, independent Git evidence, packet scope, global claims, and dependencies before reviewability.
- **REQ-193-06**: Verification requirements MUST derive deterministically from authoritative changed paths, complexity, and risk triggers.
- **REQ-193-07**: Canonical verification authority MUST be `github_actions_exact_head`; a passing referenced GitHub Actions run MUST target the exact candidate head. Historical `kis_local_exact_head` and local/VM runner authority MUST NOT be restored.
- **REQ-193-08**: Integration admission remains serialized and single-owner; actual GitHub mutation remains delegated to existing registered exact-head GitHub operations.
- **REQ-193-09**: Preserve distinct `worker_done`, `reviewable`, `integrating`, `delivered`, `commissioning`, and `closed` semantics.

## Acceptance

1. Historical coordinator focused tests are restored and pass after the authority seam is updated.
2. Stale authority, scope, dependency, runtime, or Git evidence fails closed.
3. Duplicate accepted reconciliation is idempotent and consumed authority cannot authorize a different handoff.
4. Verification requirements are stable for identical authoritative inputs and emit `github_actions_exact_head` only.
5. Missing, failed, stale, unreferenced, or wrong-SHA GitHub Actions evidence cannot authorize delivery.
6. Integration queue ownership remains serialized under contention and crash/retry paths remain deterministic.
7. No VirtualBox, disposable Windows runner, local Actions replacement, or crisis-era local-verifier dependency is introduced.
## Risks and recovery

- Durable coordinator state is correctness-sensitive; retain cross-process serialization, strict schema validation, and fail-closed recovery.
- Historical source is evidence, not current authority. Any conflict with reconstructed repository rules is resolved in favor of current repository authority.
- Recovery is revert of this isolated change; no existing coordinator state exists on reconstructed main to migrate in place.

## Out of scope

- Historical #253 telemetry, Control Center projection, operator UX, and commissioning work.
- Any local/VM/disposable-Windows replacement for GitHub Actions.
- Replacing registered GitHub merge/refresh/cleanup primitives.
- Unrelated Work Management, verification-runner, or infrastructure changes.