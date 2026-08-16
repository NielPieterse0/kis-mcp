# Workflow Import Cycle Implementation Plan

**Goal:** Eliminate the deterministic tools-first circular import while preserving public workflow-package behavior.

**Architecture:** Keep workflow submodules independently importable by removing eager platform composition from package initialization. Resolve the existing `workflow_descriptors` public export only when callers request it.

**Tech Stack:** Python 3.13, pytest, subprocess-based clean-import regression tests, KIS change governance.

## Global constraints

- Stay inside `scope.json`.
- Add and run the failing regression test before production code changes.
- Preserve public imports and avoid unrelated dependency refactors.

### Task 1: Lock the import-order regression

**Files:**
- Modify: `src/kis_mcp/workflows/__init__.py`
- Test: `tests/workflows/test_import_order.py`

- [x] Add clean-process tests for tools-first, workflows-first, and the public `workflow_descriptors` export.
- [x] Confirm tools-first fails for the current circular-import reason.
- [x] Implement the smallest lazy package-export change.
- [x] Run focused and affected verification.
- [x] Review the exact diff and run governed scope checks.
