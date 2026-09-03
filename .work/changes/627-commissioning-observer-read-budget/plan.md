# Commissioning Observer Read Budget Implementation Plan

> **For agentic workers:** Execute this plan task-by-task and keep the declared scope current.

**Goal:** Fix issue 641 so the bounded post-merge commissioning observer can process the configured candidate window without deterministic external-read starvation, while preserving exact identity, checkpoints, and fail-closed candidate evidence.

**Architecture:** Keep candidate discovery separately bounded, create a fresh external-read counter for each discovered candidate, and share one mutation budget across the full scan. Candidate read-budget exhaustion is ordinary retryable per-candidate evidence; mutation-budget exhaustion remains a whole-scan safety failure.

**Tech Stack:** Python 3.11, asyncio, pytest, repository change-governance scripts, GitHub exact-head Actions.

## Global constraints

- Stay inside `scope.json`.
- Preserve exact merge/source/change identity and checkpoint semantics.
- Keep total scan reads deterministic from configured `max_candidates` and `max_external_reads`.
- Do not alter Work hard rules, restart authority, or mutation limits.

---

### Task 1: Reproduce and bound starvation

**Files:**
- Modify: `.work/changes/627-commissioning-observer-read-budget/{spec,plan,tasks,closeout}.md`
- Test: `tests/post_merge_commissioning/test_runtime_service.py`

- [x] Reconcile issue #641 against live Work/GitHub identity.
- [x] Add a multi-candidate regression that exceeds the former cumulative shared read counter.
- [x] Confirm focused runtime-service tests pass with the candidate-isolated design.

### Task 2: Implement budget isolation

**Files:**
- Modify: `src/kis_mcp/commissioning_runtime/service.py`
- Test: `tests/post_merge_commissioning/test_runtime_service.py`

- [x] Split discovery and candidate external-read counters.
- [x] Preserve one shared mutation counter across all candidates.
- [x] Convert per-candidate read exhaustion to bounded unresolved evidence while preserving the checkpoint.
- [x] Prove later candidates still execute after an earlier candidate exceeds its read allowance.

### Task 3: Reconcile operations and verification

**Files:**
- Modify: `docs/operations/post-merge-commissioning.md`
- Verify: focused commissioning suite, change check, review, exact-head CI, live observer acceptance.

- [x] Document budget semantics and deterministic total ceiling.
- [x] Run focused post-merge commissioning tests.
- [ ] Run `pwsh -File scripts/change-workflow.ps1 check`.
- [ ] Review the bounded change and resolve findings.
- [ ] Publish, obtain exact-head CI, merge, refresh, and clean up.
- [ ] Prove live observer reaches PR #628 and a fresh governed follow-up merge without checkpoint edits.
