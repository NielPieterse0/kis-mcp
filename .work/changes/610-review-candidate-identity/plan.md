# Review Candidate Identity Implementation Plan

**Goal:** Complete #587 without crossing #588/#569 ownership.

**Architecture:** Keep review closure and correction targeting in `review.py`; derive candidate source/policy/runtime identity and deterministic scenarios in `candidate_runtime.py`; integrate only the required candidate/review entry points in coordinated `tools.py`.

**Tech Stack:** Python 3.13 via `uv`, FastMCP, Git identity, pytest, Ruff, repository change governance.

## Global constraints

- Stay inside `scope.json`.
- Keep #588 contracts/promotion/evidence/state excluded.
- Keep `src/kis_mcp/skills/**` excluded.
- Fail closed on candidate identity mismatch or drift.
- Preserve legacy candidate cleanup compatibility without allowing legacy reuse.

### Task 1: Review closure

- [x] Validate completed substantive reviews and reject open material findings.
- [x] Emit canonical `review_closed` evidence through `ReviewClosure`.
- [x] Select correction re-review domains only from directly affected material findings.

### Task 2: Candidate identity and reuse

- [x] Bind source commit/tree, policy/runtime fingerprints, endpoint and existing Work/server/process identity.
- [x] Reuse only exact v2 candidates and fail closed on mismatch/drift.
- [x] Preserve safe cleanup for legacy receipts while requiring upgrade before reuse.

### Task 3: Live scenarios

- [x] Select deterministic scenarios from affected surfaces/tools.
- [x] Preserve effect boundaries and negative/failure paths.
- [x] Make manual scenario assembly optional for the normal path.

### Task 4: Verify and close

- [x] Add focused acceptance tests.
- [x] Run affected once-through tests and lint.
- [ ] Run governance check, independent review, publication CI, merge, and cleanup.
