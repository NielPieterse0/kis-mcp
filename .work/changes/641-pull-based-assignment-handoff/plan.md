# Pull Based Assignment Handoff Implementation Plan

**Goal:** Complete #544's missing pull-resume handoff without duplicating Work or coordinator authority.

**Architecture:** Reuse the existing Work activation materializer. `project_management_current_work` first reads authoritative Project state and selects the unique Active item for the requested owner; only then does it materialize the existing persisted handoff. The top-level project-management registration forwards the same materializer already used by claim/take-next. No new durable store or coordinator contract is introduced.

**Tech Stack:** Python, FastMCP, existing Work Management board/activation services, pytest, KIS change governance.

## Global constraints

- Stay inside `scope.json` and avoid #619-owned paths.
- Preserve Work Management as command authority and coordinator authority semantics.
- Add focused regression coverage before completion.
- Do not introduce push-launch semantics or conversation-derived authority.

### Task 1: Resume handoff

- [x] Add regression tests for exact-owner resume, wrong-owner fail-closed behavior, and production registration wiring.
- [x] Forward the activation materializer through enhancement registration.
- [x] Materialize the persisted handoff only after authoritative Active-owner selection.
- [x] Confirm focused project-management tests pass.

### Task 2: Documentation and governance

- [x] Reconcile the coordinator module contract with the Work-facing pull boundary.
- [x] Keep active parallel-owner paths excluded and validate scope.
- [x] Run governed change check and review the final diff.
- [x] Resolve blocking findings and complete verification evidence.

