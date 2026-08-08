# CI Governance Validation Implementation Plan

> **For agentic workers:** Execute this plan task-by-task and keep the declared scope current.

**Goal:** Allow isolated CI governance validation without requiring unrelated local worktrees while preserving strict local validation.

**Architecture:** Keep `validate_repository` strict by default, add an explicit switch that skips only the final active-worktree-presence requirement, expose it as `validate --claims-only`, and use that mode only from isolated Work Management CI.

**Tech Stack:** Python 3.13, pytest, PowerShell, GitHub Actions.

## Global constraints

- Stay inside `scope.json`.
- Add tests before behavior changes.
- Do not alter unrelated authority or policy.
- Do not close or clean unrelated active worktrees.

---

### Task 1: Repair isolated CI governance validation

**Files:**
- Modify: `scripts/change-governance.py`, `.github/workflows/work-management.yml`
- Test: `tests/test_change_governance.py`, `tests/work_management/test_ci_workflow.py`

- [x] Write the failing isolated-CI regression.
- [x] Confirm the expected failure.
- [x] Implement the smallest complete change.
- [x] Confirm focused, scope, diff, and repository verification pass.
