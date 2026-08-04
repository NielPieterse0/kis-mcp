# Parallel Agent Governance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a lean, machine-checked change-claim workflow that supports unrestricted parallel agents without duplicate scope.

**Architecture:** A single stdlib Python command owns claim validation, worktree creation, scope checking, listing, and safe cleanup. Tracked templates and repository instructions define the human workflow; `scripts/verify.py` validates the committed governance layout.

**Tech Stack:** Python 3.11–3.13 standard library, PowerShell 7, Git, pytest.

## Global Constraints

- Worktrees use `.work/worktrees/<change-id>`.
- Change artifacts use `.work/changes/<change-id>/`.
- No limit is placed on active agents or worktrees.
- No force deletion, external service, runtime policy change, or new dependency.
- Path claims support exact repository-relative paths and recursive `/**` suffixes only.

---

### Task 1: Claim model and conflict detection

**Files:**
- Create: `tests/test_change_governance.py`
- Create: `scripts/change-governance.py`

**Interfaces:**
- Produces: `ChangeClaim`, `ClaimError`, `find_claim_conflicts()`, `paths_outside_claim()`.

- [ ] Write failing tests for structural validation, duplicate outcomes, exclusive overlap, coordinated shared overlap, and diff-to-scope checking.
- [ ] Run the focused tests and confirm they fail because the module does not exist.
- [ ] Implement the minimal claim model and pure validation functions.
- [ ] Run the focused tests and confirm they pass.

### Task 2: Worktree lifecycle commands

**Files:**
- Modify: `tests/test_change_governance.py`
- Modify: `scripts/change-governance.py`
- Create: `scripts/change-workflow.ps1`

**Interfaces:**
- Produces CLI commands: `new`, `validate`, `check`, `list`, `cleanup`.

- [ ] Add failing integration tests using temporary Git repositories for standardized creation and safe cleanup refusal.
- [ ] Run focused tests and confirm expected failures.
- [ ] Implement Git worktree discovery, creation, current-change checks, listing, and non-force cleanup.
- [ ] Add the locked PowerShell wrapper.
- [ ] Run focused tests and confirm they pass.

### Task 3: Templates and repository authority

**Files:**
- Create: `.work/changes/_template/scope.json`
- Create: `.work/changes/_template/spec.md`
- Create: `.work/changes/_template/plan.md`
- Create: `.work/changes/_template/tasks.md`
- Create: `.work/changes/_template/closeout.md`
- Modify: `.gitignore`
- Modify: `AGENTS.md`
- Modify: `docs/OPERATIONS.md`

- [ ] Add tracked templates with concrete required fields and no new product authority.
- [ ] Document creation, checking, coordination, and cleanup rules.
- [ ] Ignore only `.work/worktrees/`, retaining change artifacts under version control.

### Task 4: Verification integration

**Files:**
- Modify: `tests/test_repository_scope.py`
- Modify: `scripts/verify.py`

- [ ] Add failing repository-scope tests for the worktree ignore rule, templates, command, and authority text.
- [ ] Run focused tests and confirm expected failures.
- [ ] Add committed-layout verification to `scripts/verify.py`.
- [ ] Run focused tests and full `scripts/verify.ps1`.

### Task 5: Review and closeout

**Files:**
- Modify: `.work/changes/001-parallel-agent-governance/tasks.md`
- Modify: `.work/changes/001-parallel-agent-governance/closeout.md`
- Modify: `.work/changes/001-parallel-agent-governance/scope.json`

- [ ] Run `scripts/change-workflow.ps1 check`.
- [ ] Run `git diff --check` and inspect the complete diff.
- [ ] Run `scripts/verify.ps1` on the final state.
- [ ] Record evidence, set the change status to `closed`, commit, merge to `main`, and safely remove the worktree.
