# Tasks: Parallel Agent Coordinator — Slice 5 (#251)

## Prerequisites

- [x] #247 architecture/contracts completed and preserved.
- [x] #248 atomic reservation admission completed and preserved.
- [x] #249 scope-revision/lease/fence authority lifecycle completed and preserved.
- [x] #250 deterministic planning/runtime binding/work packets completed and preserved.
- [x] Parent branch reconciled first onto `main` `cf17056b2a10d7111be4e87f91cfbffc4645e925` (`93b341e`), then refreshed after concurrent #270 landed and reconciled onto current `main` `e238067169a272e3cb3c6284264653557ba7306b` via merge `3084e56`.
- [x] #241/#251 re-read; canonical `develop-code`, `develop-docs`, and `mcp-development` procedures loaded.
- [x] #278 re-read and confirmed active in `163-state-ownership-namespace`; its task record still has the resolver/module implementation outstanding, so no consumable ownership/namespace API is available yet.
- [x] Strict `247 -> 248 -> 249 -> 250 -> 251 -> 252 -> 253` sequencing preserved.

## Slice 5 implementation

- [x] Add strict worker-execution lifecycle/correlation contract.
- [x] Add deterministic location-independent worker execution transition model.
- [x] Add idempotent duplicate/stale event handling.
- [x] Add ephemeral MCP connect/discover/filter/invoke/cleanup/reconnect adapter.
- [x] Enforce current reservation authority before filtered exposure and immediately before mutating invocation.
- [x] Extend worker-handoff correlation without implementing #252 reconciliation.
- [ ] Consume #278 durable-evidence namespace resolver for persistent execution journal/store. **Blocked: #278 resolver not implemented yet.**
- [ ] Add restart/recovery and resume/retry behavior after #278 contract is available. **Blocked by #278.**

## Slice 5 gates

- [x] Focused Slice 5 tests pass.
- [x] Full coordinator regression suite passes (**78/78** after API-contract corrections).
- [x] Strict coordinator schemas validate emitted Slice 5 values.
- [x] Ruff, Python compilation, governed scope check, and `git diff --check` pass.
- [x] Required reviews are clean for implemented scope: code-quality corrective commits have zero findings; architecture corrective range has zero findings and confirms the #278 persistence boundary; final API-contract corrective range `b22e9d8..2ec02d4` has zero findings. Persistence/restart implementation itself remains blocked on #278 and is not claimed complete.

## Explicit stop/dependency

- #278 owns typed state ownership and deterministic namespace resolution.
- Do not create a new #251 persistence root or duplicate #278 ownership classes while that contract is unavailable.
- If location-independent lifecycle/MCP work is complete first, stop with #251 open at the persistence/restart dependency rather than crossing lanes.
