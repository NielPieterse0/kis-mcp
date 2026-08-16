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
- [x] Serialize conflicting lifecycle updates with the existing cross-platform OS file-lock primitive and make mutation receipt claims single-winner through exclusive file creation.
- [x] Fsync durable snapshots/receipts before atomic replacement/dispatch evidence is relied upon.
- [x] Keep `WorkerExecutionStore` internal rather than expanding the coordinator package API.
- [x] Keep MCP reconnect/discovery/session objects ephemeral and non-authorizing.

## Slice 5 gates

- [x] Focused worker persistence/lifecycle/MCP tests pass (**26/26**).
- [x] Full coordinator regression suite passes (**84/84**).
- [x] Strict coordinator schemas validate emitted Slice 5 values through the coordinator regression suite.
- [x] Ruff and Python compilation pass on the final implementation state.
- [x] Governed change check and `git diff --check` pass on the final implementation state.
- [x] Code-quality corrective review `7423a83` reports zero findings.
- [x] API/contracts corrective review `7423a83` reports zero findings.
- [x] Architecture corrective review `7423a83` completed with no blocking defect; its only action was repository-wide verification that no package-level `WorkerExecutionStore` consumers remained, and that search returned zero matches.
- [x] Persistence/recovery review findings were resolved: explicit receipt identity validation, contention tests, fsynced durable writes, and internal-only store exposure were added. Later compatibility concerns were disproven by repository evidence: receipt v1/store are new in unmerged #251, every receipt builder already writes `execution_id`/`result_id`, and no package-level store imports exist.
- [x] Final documentation/review evidence prepared for freeze; exact-head local verification is rerun after commit without further modification.

## Landing stop

- #251 must not merge until provider-native GitHub Actions canonical verification succeeds for the exact frozen head.
- The disposable Windows Actions runner needed for that canonical evidence is not yet commissioned.
- Do not waive or substitute local evidence for the exact-head CI requirement.
- Do not begin #252 from this lane.
