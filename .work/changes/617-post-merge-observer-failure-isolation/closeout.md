# Closeout: Post-Merge Observer Failure Isolation

## Implemented scope

- Isolated retryable candidate-processing failures inside the bounded observer scan.
- Added typed `unresolved_candidate` receipt evidence without provider exception detail.
- Preserved checkpoint non-advancement whenever any candidate remains unresolved.
- Preserved whole-scan handling for shared budget/discovery failures and the existing no-self-restart boundary.
- Updated the canonical commissioning runbook for the new retryable-candidate behavior.

## Validation evidence

- Focused runtime service tests: `16 passed` with `python -m pytest -p no:asyncio tests/post_merge_commissioning/test_runtime_service.py -q`.
- Diff/style checks: `git diff --check` and focused Ruff checks passed.
- Governed scope check: `pwsh -File scripts/change-workflow.ps1 check` passed.
- Broader commissioning collection was attempted but the ambient Python environment lacks `fastmcp_tasks`; exact-head GitHub verification remains authoritative.

## Live defect evidence

- Current observer receipt scanned 24 candidates, successfully accounted PR #565 / change `258-defender-safe-agnix`, then failed globally before candidate #570 was recorded.
- PR #570 is change `256-state-ownership-diagnostics-cleanup`, source issue #550.
- Its landed schema-v4 scope records change ID `256-state-ownership-diagnostics-cleanup`; the current historical Work card for #550 has `change_id=null`, so Work corroboration correctly remains retryable/unresolved.

## Review

- Initial code-quality review found heterogeneous candidate failures could be summarized using only the first error type.
- Resolution: retain exact per-candidate error types and use `MultipleCandidateErrors` only for heterogeneous run-level aggregation.
- Current-state code-quality re-review: no findings.

## Git and merge

- Branch: `change/617-post-merge-observer-failure-isolation`
- Worktree: `.work/worktrees/617-post-merge-observer-failure-isolation`
- Commit: pending publication step.
- Pull request / exact-head verification / merge: pending.
- Post-merge live observer proof and cleanup: pending.

## Residual items

- Historical issue #550 remains intentionally unresolved evidence until authoritative Work corroboration exists; the fix prevents it from globally wedging later candidates without advancing past it.
