# Inspect Change Native Git Semantics Implementation Plan

> **For agentic workers:** Execute this plan task-by-task and keep the declared scope current.

**Goal:** Fix #273 by preserving native Git line-ending comparison semantics inside KIS's bounded local change reader without re-enabling arbitrary system/global Git behavior.

**Architecture:** Keep the existing isolated Git execution path. Add a bounded read-only probe for effective native line-ending configuration (`core.autocrlf` and `core.eol`), validate the returned values, and replay only those values as explicit `-c` options for diff/status evidence commands. Existing repeated inventory and guard reads continue to invalidate materially changing evidence during inspection.

**Tech Stack:** Python 3.11+, local Git CLI, pytest, Ruff, KIS change governance.

## Global constraints

- Stay inside `scope.json`.
- Add tests before behavior changes.
- Do not re-enable arbitrary system/global Git configuration, global attributes, external diff/text conversion, credentials, prompts, hooks, or network behavior.
- Preserve existing metadata validation, deadlines, output budgets, and source-race diagnostics.

---

### Task 1: Lock the regression

**Files:**
- Modify: `tests/discover/test_local_change_inventory.py`
- Modify: `tests/discover/test_change_targets.py`
- Modify: `tests/discover/test_git_hardening.py`

- [x] Add a deterministic system-config fixture with `core.autocrlf=true` and a linked CRLF worktree.
- [x] Prove native Git reports the linked worktree clean while current KIS reports false modifications.
- [x] Add linked-worktree staged/unstaged/untracked equivalence coverage and repository-attribute coverage.

### Task 2: Preserve bounded native line-ending semantics

**Files:**
- Modify: `src/kis_mcp/discover/git_reader.py`

- [x] Add a bounded native semantic-config probe that strips repository-selection environment overrides but does not suppress config while querying.
- [x] Validate and replay only supported line-ending values into the isolated Git command prefix.
- [x] Ensure working-tree guards and mutable fingerprints use the same resolved semantics and fail safely when the probe is unavailable or changes.
- [x] Keep existing external-diff, textconv, attribute-file, exclude-file, credential, pager, prompt, and optional-lock controls unchanged.

### Task 3: Verify and review

**Files:**
- Review all change-160 owned paths.

- [x] Run focused Discover tests for local inventory and change targets.
- [x] Run Ruff on changed Python files.
- [x] Run `git diff --check`.
- [x] Run `pwsh -File scripts/change-workflow.ps1 check`.
- [x] Review the final diff against #273 acceptance criteria and record closeout evidence.
