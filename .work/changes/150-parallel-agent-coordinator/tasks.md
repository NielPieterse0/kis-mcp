# Tasks: Parallel Agent Coordinator — Slice 4 (#250)

## Prerequisites

- [x] #247 architecture/contracts completed and preserved.
- [x] #248 atomic reservation admission completed and preserved.
- [x] #249 scope-revision/lease/fence authority lifecycle completed and preserved.
- [x] Slice 4 started from parent handoff `aa369eb` on verified `main` `7d4391873b17064fcb1ce32c1dc3915a4b6a0cf4`.
- [x] Repository authority and #241/#250 re-read; canonical `develop-code`, `develop-docs`, and review procedures loaded.
- [x] Strict `247 -> 248 -> 249 -> 250 -> 251 -> 252 -> 253` sequencing preserved.

## Slice 4 implementation

- [x] Add test-first deterministic DAG planning with dependency endpoint/cycle validation.
- [x] Reject unresolved exclusive ownership and ambiguous shared-hotspot integration ownership.
- [x] Derive ready frontier from the complete dependency + integration DAG and reject combined execution cycles.
- [x] Emit explicit integration hotspots and bounded deterministic concurrency recommendations.
- [x] Keep planning read-only and independent of mutation authority.
- [x] Resolve exact advisory worker/runtime/tool/protocol/interface/endpoint/binding evidence from injected capability discovery.
- [x] Structurally prohibit runtime discovery from granting mutation authority.
- [x] Issue self-sufficient work packets with frozen reservation/revision/lease/fence authority, exact base, scope, acceptance, verification, runtime-binding reference, and handoff requirements.
- [x] Keep packet IDs stable across lease/fence/runtime reassignment evidence while issuing one generation-1 opaque assignment key.
- [x] Persist only the assignment-key SHA-256 digest plus bounded packet evidence; plaintext assignment keys are not durable state.
- [x] Keep Slice 4 internal; no worker lifecycle, reconciliation, integration, telemetry, public MCP tool, PR, or landing behavior added.

## Slice 4 gates

- [x] Final affected regression set passes: 104/104 across change-governance, full coordinator, and impact-selected planner/model/schema tests.
- [x] `dependency-dag`, `runtime-binding`, and `work-packet` emitted values validate against their revised strict v1 schemas.
- [x] Required packet handoff fields exactly match the existing `worker-handoff` required contract minus schema metadata; that #251-owned schema was not modified.
- [x] Ruff lint, Python compilation, governed scope check, and `git diff --check` pass on the final implementation diff.
- [x] Required code-quality, architecture, and API-contract reviews have zero blocking findings after fixes and exact-diff fallback adjudication.
- [x] Slice 4 implementation commit `913de89466e8b0da5de5a7cf2b55a7b46198a520` recorded; parent change remains active and #251 is not started.

## Explicitly deferred

- Refresh/reconcile the parent branch onto current `main` before any eventual PR/landing; `main` advanced to `7bd2080ab961661ba889aa60682eaa0f2406cf7d` after change 154 landed.
- #251 durable worker execution, retry/resume, assignment-key lifecycle beyond initial issuance, and MCP worker adapter behavior.
- #252 handoff/assignment-key reconciliation, verification derivation, serialized integration, and landing.
- #253 observability, evaluation, operator UX, Control Center integration, and commissioning.
