# Tasks: Parallel Agent Coordinator — Slice 5 (#251)

## Prerequisites

- [x] #247 architecture/contracts completed and preserved.
- [x] #248 atomic reservation admission completed and preserved.
- [x] #249 scope-revision/lease/fence authority lifecycle completed and preserved.
- [x] #250 deterministic planning/runtime binding/work packets completed and preserved.
- [x] Parent branch reconciled with current `main` after #278 landed; no #278 implementation was authored in this lane.
- [x] #241/#251 re-read; canonical `develop-code`, `develop-docs`, and `mcp-development` procedures loaded.
- [x] Landed #278 state ownership API re-read from repository truth and consumed directly.
- [x] Strict `247 -> 248 -> 249 -> 250 -> 251 -> 252 -> 253` sequencing preserved.

## Slice 5 implementation

- [x] Add strict worker-execution lifecycle/correlation contract.
- [x] Add deterministic location-independent worker execution transition model.
- [x] Add idempotent duplicate/stale event handling.
- [x] Add ephemeral MCP connect/discover/filter/invoke/cleanup/reconnect adapter.
- [x] Enforce current reservation authority before filtered exposure and immediately before mutating invocation.
- [x] Extend worker-handoff correlation without implementing #252 reconciliation.
- [x] Consume #278 `DURABLE_EVIDENCE` namespace resolution plus `derive_change_source_id(change_id)` for the persistent execution store; no alternate root/source convention added.
- [x] Restore ordered execution state after restart and preserve idempotent persisted resume/retry.
- [x] Persist write-ahead mutation receipts so completed mutation retries reuse the stored result and uncertain in-flight work is not executed twice.
- [x] Keep durable result/effect evidence tied to execution/attempt, reservation/revision/lease/fence, runtime binding, tool arguments, progress, and result identity.
- [x] Keep MCP reconnect/discovery/session objects ephemeral and non-authorizing.

## Slice 5 gates

- [x] Focused worker persistence/lifecycle/MCP tests pass (**23/23**).
- [x] Full coordinator regression suite passes (**81/81** before final documentation-only reconciliation).
- [x] Strict coordinator schemas validate emitted Slice 5 values through the coordinator regression suite.
- [x] Ruff and Python compilation pass on the implementation state.
- [ ] Final governed change check and `git diff --check` on the complete #251 diff.
- [ ] Final specialist review programme: code quality, architecture, API/contracts, persistence/recovery.
- [ ] Final review findings, if any, resolved and corrective ranges re-reviewed.
- [ ] Final #251 commit frozen for canonical exact-head GitHub Actions verification.

## Landing stop

- #251 must not merge until provider-native GitHub Actions canonical verification succeeds for the exact frozen head.
- The disposable Windows Actions runner needed for that canonical evidence is not yet commissioned.
- Do not waive or substitute local evidence for the exact-head CI requirement.
- Do not begin #252 from this lane.
