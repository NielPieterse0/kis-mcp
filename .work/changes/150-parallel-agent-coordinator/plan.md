# Parallel Agent Coordinator Slice 4 Implementation Plan

> Execute #250 inside the existing `150-parallel-agent-coordinator` worktree. Preserve #247-#249 and do not begin #251.

**Goal:** Compile authoritative task inputs into deterministic parallel work, then issue bounded self-sufficient work packets with exact advisory runtime/capability identity while preserving Slice 3 as the sole mutation-authority source.

**Architecture:** Add one internal planner module. `PlannerService` is read-only and validates task/dependency/path topology before emitting a canonical DAG, ready frontier, hotspots, and concurrency recommendation. `WorkPacketService` resolves exact runtime candidates, freezes Slice 3 authority into packets, issues an opaque assignment key, and persists only bounded packet/assignment evidence beneath the coordinator state root.

**Development level:** Complex. #250 revises strict coordinator contracts and crosses planning, generated-state, capability-discovery, and mutation-authority boundaries. The operator assignment plus #241/#250 provide the approved product/architecture direction.

## Constraints

- Stay inside parent coordinator-owned paths.
- Preserve HR-001 / HR-002 / HR-003 exactly.
- Preserve #248 reservation and #249 scope/lease/fence semantics unchanged.
- Registry/catalog/runtime evidence is advisory and never grants mutation authority.
- Do not add public MCP coordinator tools in this slice.
- Do not implement #251 workers, #252 reconciliation/integration, or #253 telemetry/commissioning.
- Do not push, open a PR, merge, clean up, or restart runtimes for this slice.

### Task 1: Slice 4 RED tests and contract refinement

**Requirements:** REQ-250-01 through REQ-250-10.

- [x] Add RED tests for deterministic DAG production, cycles/endpoints, ownership/hotspot validation, runtime resolution, packet completeness, stable packet identity, and assignment-key storage.
- [x] Refine `dependency-dag`, `runtime-binding`, and `work-packet` v1 schemas for Slice 4-owned behavior while preserving strict closed contracts.

### Task 2: Deterministic planner

**Requirements:** REQ-250-01 through REQ-250-04, REQ-250-09.

- [x] Add validated planner task/request models with deterministic normalized inputs.
- [x] Validate dependency endpoints, self-dependencies, dependency cycles, combined execution cycles, exclusive overlaps, and shared-hotspot ownership.
- [x] Emit canonical nodes/edges, ready frontier, hotspot evidence, and deterministic recommended concurrency.

### Task 3: Runtime binding and work-packet issuance

**Requirements:** REQ-250-05 through REQ-250-08.

- [x] Resolve exact worker/runtime/tool/protocol/interface/endpoint/binding evidence from injected discovery candidates.
- [x] Reject candidates that do not satisfy required capabilities or that claim mutation authority.
- [x] Compute and validate immutable runtime-binding fingerprints.
- [x] Issue schema-valid work packets with frozen Slice 3 authority and required handoff fields.
- [x] Derive reassignment-stable packet IDs, issue generation-1 opaque assignment keys, and persist only assignment-key digests.

### Task 4: Documentation, review, verification, and handoff

**Requirements:** REQ-250-01 through REQ-250-10.

- [x] Update the coordinator module product spec with cumulative Slice 4 implementation status and strict #251+ boundaries.
- [x] Run focused Slice 4 tests plus the full coordinator regression suite and impact-selected affected tests.
- [x] Run Python compilation, Ruff lint, `git diff --check`, and governed scope check on the final implementation diff.
- [x] Perform required `code-quality`, `architecture`, and `api-contracts` reviews and resolve blocking findings; retain automated reviewer timeouts as non-pass evidence and use exact-diff fallback.
- [x] Commit Slice 4 implementation on the existing parent branch and record exact handoff evidence. Leave the parent governed change active for #251.
