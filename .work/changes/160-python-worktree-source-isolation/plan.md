# Python Worktree Source Isolation Implementation Plan

> **For agentic workers:** Execute this plan task-by-task and keep the declared scope current.

**Goal:** Bind KIS-launched registered repository/worktree processes to the selected checkout's Python source without mutating shared virtualenvs.

**Architecture:** Add one repository-process environment normalizer at the existing ThreeRule middleware call boundary. Reuse shell-state parsing to determine each executable segment's effective cwd, resolve the nearest registered Git checkout/worktree, and derive `<checkout>/src`. Inject process-local `PYTHONPATH` only when one authoritative source root exists; reject ambiguous/unsafe binding. Remove verification's private source injection so all nested verification launches consume the generic middleware contract.

**Tech Stack:** Python 3.13, FastMCP middleware, existing shell parser and project registry, pytest, PowerShell/cmd command rendering.

## Global constraints

- Stay inside `scope.json` and preserve concurrent path claims.
- Add failing tests before production behavior changes.
- Do not alter HR-001/002/003, provider schemas, or virtualenv contents.
- Keep source identity ephemeral/process-local; #278 remains authority for persistent state ownership.

### Task 1: Lock source-resolution and failure behavior

**Files:** `tests/test_process_environment.py`, `src/kis_mcp/process_environment.py`

- [x] Add failing tests for nearest worktree `src`, non-applicable paths, PowerShell/cmd binding, explicit `PYTHONPATH` override rejection, multi-worktree ambiguity, and shared editable-path regression.
- [x] Confirm the tests fail because the generic process normalizer does not exist.
- [x] Implement the smallest deterministic normalizer and typed errors.
- [x] Run the focused process-environment tests.

### Task 2: Wire the generic process boundary

**Files:** `src/kis_mcp/middleware.py`, `src/kis_mcp/gateway/composition.py`, `tests/test_process_environment.py`

- [x] Add middleware tests proving normalized arguments reach both policy resolution and provider execution.
- [x] Wire the normalizer into gateway composition with the live project registry.
- [x] Preserve existing line-ending normalization and process-state observation behavior.
- [x] Run focused middleware/process tests.

### Task 3: Reconcile verification to the generic contract

**Files:** `src/kis_mcp/workflows/verification/execution.py`, `tests/workflows/verification/test_verification_execution.py`

- [x] Change verification tests to require project selection but no private `PYTHONPATH` implementation.
- [x] Remove verification-only source injection.
- [x] Prove the generic normalizer binds source-sensitive launches through the process boundary.
- [x] Run focused verification tests.

### Task 4: Review and verify

- [x] Run `pwsh -File scripts/change-workflow.ps1 check`.
- [x] Run focused tests for process environment, middleware interaction, and verification execution.
- [x] Run affected verification appropriate for concurrent local execution; 42 direct changed-surface tests, `py_compile`, scope check, and diff check pass. Canonical full verification remains exact-head CI.
- [x] Run required review gates; iterative Codex findings were fixed, final hardening Codex review is clean, and final-range architecture/API-contract reviews have no actionable findings.
- [x] Prepare final closeout evidence and a reviewable local source tree for governed PR reconciliation.
- [x] Record the source-identity handoff on #278.
- [ ] Finalize #265 delivery evidence through exact-head CI, merge, and governed cleanup; those facts remain GitHub/Git authority rather than pre-merge repository metadata.
