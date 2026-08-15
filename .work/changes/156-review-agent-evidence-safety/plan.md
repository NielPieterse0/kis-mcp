# Review Agent Evidence Safety Implementation Plan

> **For agentic workers:** Execute this plan task-by-task and keep the declared scope current.

**Goal:** Close #267 with source-bound review evidence, shared deadline budgets, strict result validation, and explicit evidence coverage.

**Architecture:** Reuse Discover `InspectChangeService`/`GitChangeReader` as the canonical source-identity authority. The review collector packages whole per-file patches for that exact source and exposes coverage metadata. Review backends receive only remaining deadline budget. Change execution passes the exact source selector into every specialist review and validates review provenance against verification selection before accepting completion.

**Tech Stack:** Python 3.11+, FastMCP, Discover Git readers/contracts, pytest, GitHub Actions, governed change workflow.

## Global constraints

- Stay inside `scope.json` and #267.
- Preserve benchmark behavior and unrelated provider/tool semantics.
- Add or revise focused regression tests before relying on behavior changes.
- No full local canonical verifier before PR; PR CI owns the canonical verifier.
- Do not claim #261 or #265 resolved unless separately evidenced.

---

### Task 1: Bind reviewer evidence to canonical change source

**Files:**
- Modify: `src/kis_mcp/workflows/code_review/contracts.py`, `evidence.py`, `tools.py`, `reviewer.py`, `src/kis_mcp/workflows/verification/selection.py`, workflow composition.
- Test: `tests/workflows/code_review/test_evidence.py`, `test_reviewer.py`, `tests/workflows/verification/test_verification_selection.py`.

- [x] Add canonical source selector parameters and provenance contract.
- [x] Use Discover change identity as the review source fingerprint.
- [x] Package deterministic whole-file evidence with explicit omission metadata.
- [x] Cover commit/range review with unrelated working-tree dirt.

### Task 2: Enforce one deadline budget

**Files:**
- Modify: reviewer, change execution, NVIDIA client, Codex adapter, review settings/schema.
- Test: reviewer/change-execution/provider/tool focused tests.

- [x] Add configured total review deadline.
- [x] Pass only remaining budget to each backend attempt.
- [x] Bound the aggregate specialist-review phase in change execution.
- [x] Return typed deadline exhaustion without starting later attempts.

### Task 3: Make review success structurally strict

**Files:**
- Modify: reviewer and change execution.
- Test: malformed, empty, output-limit, evidence-incomplete, and fingerprint-mismatch regressions.

- [x] Validate backend JSON before reporting `completed`.
- [x] Require KIS-owned provenance in successful results.
- [x] Reject incomplete evidence and source mismatches in change execution.

### Task 4: Reconcile docs and close

**Files:**
- Modify: `SPEC.md`, `docs/OPERATIONS.md`, change closeout artifacts.

- [x] Run focused tests and governance scope check.
- [ ] Commit exact change, prepare PR, require exact-head GitHub Actions, merge, refresh/cleanup.
- [ ] Reconcile #267 Work Management/source issue and close only after post-merge evidence.
