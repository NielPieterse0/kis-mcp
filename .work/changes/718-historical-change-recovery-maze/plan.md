# Historical Change Recovery Maze Implementation Plan

> **For agentic workers:** Execute this plan task-by-task and keep the declared scope current.

**Goal:** Make historical merged-change recovery and follow-up transfer deterministic so stale landed claims do not block safe follow-up work or force manual branch/worktree surgery.

**Architecture:** Build the inventory by change ID, let any live linked change worktree replace the stale base copy of the same claim, and only auto-close schema-v3+ base claims when no live worktree exists and that scope record is already present on its declared base. This deliberately ignores later residual commits on a preserved historical branch once its worktree is retired.

**Tech Stack:** Python change-governance logic, pytest regression coverage, PowerShell change-workflow checks.

## Global constraints

- Stay inside `scope.json`.
- Add tests before behavior changes.
- Do not alter unrelated authority or policy.

---

### Task 1: Define the bounded change

**Files:**
- Modify: `scripts/change-governance.py`
- Test: `tests/test_change_governance.py`, `tests/capabilities/test_governed_change.py`

- [x] Write the failing regression coverage.
- [x] Confirm the historical residual-branch scenario is represented.
- [x] Implement the smallest complete claim-precedence/release change.
- [x] Confirm focused verification and governance scope checks pass.
