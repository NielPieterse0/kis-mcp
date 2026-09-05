# Selection Contract Lifecycle Compat Implementation Plan

**Goal:** Restore higher-level Work lifecycle compatibility with the evolved canonical selection contract without changing selection semantics.

**Architecture:** Keep canonical selection schema ownership in `WorkSelectionContract`. Split generic lifecycle inventory fields from selection inventory fields. Next-work composes lifecycle readiness prerequisites with canonical selection fields; exact-target lifecycle commands request only lifecycle fields plus operation-specific extras.

**Tech Stack:** Python, pytest, governed change workflow.

## Global constraints

- Stay inside `scope.json`.
- Preserve canonical contract strict validation.
- Preserve #444 selection tier semantics.
- Keep exact-target resolution bounded and fail closed.

### Task 1: Reproduce and isolate

- [x] Add regression proving exact-target lifecycle inventory currently includes selection-only fields.
- [x] Confirm the regression fails before implementation.

### Task 2: Implement bounded projection

- [x] Expose canonical selection field names from the canonical contract object.
- [x] Keep lifecycle command fields independent from selection-only fields.
- [x] Compose canonical selection fields only for next-work inventory.

### Task 3: Verify behavior

- [x] Cover claim, transition, and completion field isolation.
- [x] Assert next-work requests every canonical selection field.
- [x] Run focused Work-management tests.
- [x] Run governed diff scope check.
- [x] Complete architecture and test-quality review; resolve findings.
- [ ] Run repository verification and exact-head CI.
- [ ] Merge, close Work/issue, and clean the worktree.
