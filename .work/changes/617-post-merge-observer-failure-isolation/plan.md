# Post-Merge Observer Failure Isolation Implementation Plan

**Goal:** Continue a bounded commissioning scan past retryable per-candidate failures without advancing past unresolved evidence.

**Architecture:** Keep candidate discovery and shared-budget failures at the existing whole-scan boundary. Add a nested candidate-processing boundary that emits compact `unresolved_candidate` outcomes, continues later candidates, and returns incomplete before checkpoint advancement if any candidate failed.

**Tech stack:** Python 3.11+, pytest, existing commissioning runtime/state abstractions.

## Global constraints

- Stay inside `scope.json`.
- Add regression coverage before behavior changes.
- Preserve exact merge/source/change identity and immutable `blocked_evidence` handling.
- Preserve bounded receipts and do not persist exception detail.
- Preserve the `kis-op` no-self-restart rule.

### Task 1: Reproduce the mixed-candidate wedge

- Modify `tests/post_merge_commissioning/test_runtime_service.py`.
- Model PR #565 as retryable `MergeEvidenceError` followed by a valid fresh candidate.
- Prove the existing loop aborts before the later candidate.

### Task 2: Isolate retryable candidate failures

- Modify `src/kis_mcp/commissioning_runtime/service.py`.
- Continue after bounded candidate-local retryable exceptions.
- Re-raise shared budget exhaustion to the whole-scan boundary.
- Preserve checkpoint when any candidate is unresolved.

### Task 3: Reconcile operator truth and verify

- Update `docs/operations/post-merge-commissioning.md` with the candidate-local failure/checkpoint contract.
- Run focused post-merge commissioning tests.
- Run governed scope/check checks and required reviews.
- Publish, verify exact GitHub head, merge, reconcile live observer state, and clean up only after verified merge.
