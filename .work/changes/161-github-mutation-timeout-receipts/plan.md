# GitHub Mutation Timeout Receipts Implementation Plan

> **For agentic workers:** Execute this plan task-by-task and keep the declared scope current.

**Goal:** Close #274 without creating state ownership that belongs to #278.

**Architecture:** Add deterministic stateless operation identities and five-state receipts to the three registered GitHub delivery mutations used before review. Bound each mutation with one aggregate deadline and reserve post-timeout authority checks. Extend the reviewable-PR coordinator with one aggregate deadline, stage telemetry, stable workflow identity, and `reconcile_only` authority observation. Preserve existing exact leases and PR metadata checks.

**Tech Stack:** Python 3, FastMCP, Git/GitHub CLI wrappers, pytest, KIS change governance.

## Global constraints

- Stay inside `scope.json`.
- Add tests before behavior changes.
- Do not alter unrelated authority or policy.
- Do not persist receipts/state; #278 owns durable namespace rules.
- Status/reconciliation paths must not push, create a PR, merge, delete, or configure remote state.

---

### Task 1: Lock receipt and schema contracts — REQ-003/004/005/007/008

**Files:**
- Modify: `tests/projects/test_github_exact.py`, `tests/capabilities/test_registered_commit_workflow.py`
- Implement: `src/kis_mcp/projects/github_exact.py`

- [ ] Add failing tests for stable operation IDs, `status_only`, bounded `deadline_ms`, and five-state receipts.
- [ ] Prove status-only publication and PR observation execute no remote mutation.
- [ ] Preserve exact registered repository/head/base/title/body authority.

### Task 2: Make direct delivery mutations timeout-safe — REQ-002/003/004/005/006/007/009

**Files:**
- Modify: `src/kis_mcp/projects/github_exact.py`, `tests/projects/test_github_exact.py`

- [ ] Enforce one aggregate mutation deadline across command sequences.
- [ ] Reserve bounded time after push/PR-create timeout for GitHub-authority reconciliation.
- [ ] Return `applied`, `not_started`, `failed`, or `unknown` receipts from ambiguous timeout paths.
- [ ] Make exact publish retry recover an already-applied target rather than rejecting the old expected base.
- [ ] Prove ack-loss retry cannot create a duplicate branch update or PR.

### Task 3: Bound and reconcile PR preparation — REQ-001/003/004/005/006/009

**Files:**
- Modify: `src/kis_mcp/workflows/completion/contracts.py`, `src/kis_mcp/workflows/completion/service.py`, `src/kis_mcp/workflows/completion/tools.py`
- Test: `tests/workflows/completion/test_completion_service.py`, `tests/workflows/completion/test_completion_tools.py`

- [ ] Add one aggregate `deadline_ms` and propagate only remaining time to nested verification/mutations.
- [ ] Add stable preparation operation identity, elapsed time, and stage timings to success/error contracts.
- [ ] Add `reconcile_only` mode that observes publication first and reports `not_started`, `in_progress`, `applied`, `failed`, or `unknown` without remote mutation.
- [ ] Preserve verification-before-mutation for normal execution.
- [ ] Prove partial state and deadline-stage classification.

### Task 4: Operator documentation and verification — REQ-001..009

**Files:**
- Modify: `docs/OPERATIONS.md`, this change record.

- [ ] Document deadline, operation ID, status/reconcile semantics, and #278 persistence boundary.
- [ ] Run focused tests for registered GitHub delivery and completion coordinator.
- [ ] Run governed scope check and affected lint/type/syntax checks.
- [ ] Run required code-quality, architecture, and API-contract reviews; resolve blocking findings and re-run affected evidence.
- [ ] Record residual risks and closeout evidence.
