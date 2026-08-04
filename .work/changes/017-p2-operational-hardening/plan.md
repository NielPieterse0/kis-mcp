# P2 Operational Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development for every behavior change and superpowers:verification-before-completion before any completion claim.

**Goal:** Close the three unclaimed P2 findings without overlapping active Work, Discover-response, provider, or startup slices.

**Architecture:** Add semantic declaration/handoff validation to the existing Discover budgeter; replace recursive quarantine hashing with one bounded iterative walker shared by quarantine and restore; make the repository checkout an explicit runtime prerequisite instead of implying wheel portability.

**Tech Stack:** Python 3.11+, pytest, dataclasses, pathlib/os.scandir, PowerShell repository verification.

## Global Constraints

- Preserve exactly HR-001, HR-002, and HR-003.
- Use no new runtime dependency.
- Keep settings and policy in JSON.
- Do not edit excluded active-agent paths.
- Execute red-green-refactor separately for each task.

---

### Task 1: Register and baseline the emergency-isolated slice

**Files:**
- Create: `.work/changes/017-p2-operational-hardening/{scope.json,spec.md,plan.md,tasks.md,closeout.md}`

- [x] Create branch and worktree from clean `main` after the governance command failed on the known recursive duplicate-claim defect.
- [x] Register owned, shared, excluded, dependency, and integration paths before implementation edits.
- [ ] Run focused baseline tests for budgeting, quarantine, and configuration.
- [ ] Run governance validation and record the pre-existing duplicate-claim failure.

### Task 2: Keep verification declarations and handoffs synchronized

**Files:**
- Modify: `src/kis_mcp/discover/budgeting.py`
- Modify: `tests/discover/test_budgeting.py`

- [ ] Add a failing compaction test with multiple declarations and `run_verification` handoffs where the current independent list halving creates an orphan.
- [ ] Run the single test and confirm the orphan assertion fails.
- [ ] Add declaration-ID extraction, handoff/declaration consistency validation, and paired compaction.
- [ ] Run the focused budgeting suite to green.

### Task 3: Bound quarantine hashing and listing

**Files:**
- Modify: `src/kis_mcp/quarantine_integrity.py`
- Modify: `src/kis_mcp/quarantine.py`
- Modify: `tests/test_quarantine.py`
- Create: `tests/test_quarantine_integrity.py`

- [ ] Add failing tests for entry, byte, depth, and elapsed-time exhaustion and a deeply nested tree.
- [ ] Add a failing test proving `list_records(limit=1)` does not inspect a corrupt older entry.
- [ ] Run the focused tests and confirm the expected failures.
- [ ] Implement a bounded iterative hashing API with stable limit errors and counters.
- [ ] Pass configured default limits from quarantine and restore operations.
- [ ] Stop listing after the requested bounded inspection window while preserving newest-first order.
- [ ] Run quarantine and integrity tests to green.

### Task 4: Enforce the source-checkout deployment model

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/kis_mcp/config.py`
- Modify: `tests/test_config.py`
- Create: `tests/test_distribution_model.py`
- Modify: `docs/OPERATIONS.md`

- [ ] Add failing tests proving the project does not publish a wheel target and that default loading outside a valid checkout raises `KIS_MCP_SOURCE_CHECKOUT_REQUIRED`.
- [ ] Run the focused tests and confirm current metadata/default loading fail those expectations.
- [ ] Remove the misleading explicit wheel target, declare the source-checkout deployment model in project metadata, and add a stable checkout-root validator.
- [ ] Document checkout-only startup and configuration ownership.
- [ ] Run configuration and distribution tests to green.

### Task 5: Review, integrate, and verify

**Files:**
- Update: `.work/changes/017-p2-operational-hardening/{tasks.md,closeout.md}`

- [ ] Review the diff against R1-R3 and the narrow-enforcement standard.
- [ ] Run focused tests for all changed modules.
- [ ] Run `scripts/change-workflow.ps1 check` and record the governance defect if it blocks.
- [ ] Run `git diff --check`.
- [ ] Run full `scripts/verify.ps1`.
- [ ] Record dependency status for P2 items owned by `013`, `015`, and `016`.
- [ ] Commit and push the verified branch; open a PR only when dependency ordering is safe.
