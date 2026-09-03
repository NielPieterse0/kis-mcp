# Closeout: Commissioning Observer Read Budget

## Implemented scope

- Isolated external-read accounting for candidate discovery and each discovered candidate.
- Preserved one scan-wide mutation budget shared across all candidate invokers.
- Converted per-candidate external-read exhaustion into bounded `unresolved_candidate` evidence so later candidates continue while the checkpoint remains unchanged.
- Preserved mutation-budget exhaustion as a whole-scan failure.
- Documented the bounded scan model and current deterministic external-read ceiling.

## Validation evidence

- Focused checks: `uv run pytest tests/post_merge_commissioning/test_runtime_service.py -q` — 19/19 passed; `uv run pytest tests/post_merge_commissioning -q` — 185/185 passed; targeted Ruff — passed.
- Repository verification: exact-head GitHub Actions pending publication.
- Diff scope check: `pwsh -NoProfile -File scripts/change-workflow.ps1 check` — passed on the intended 8-file governed scope.

## Review

- Findings: initial test-quality review identified missing service-level mutation-budget/checkpoint coverage.
- Resolutions: added `test_shared_mutation_budget_exhaustion_is_whole_scan_failure`; reran focused/full commissioning suites. Fresh code-quality review found no required code changes. A later test-quality reviewer retry failed at provider/output-contract level and was not treated as a pass.

## Git and merge

- Branch: `change/627-commissioning-observer-read-budget`
- Worktree: `.work/worktrees/627-commissioning-observer-read-budget`
- Commit: pending.
- Pull request or merge: pending exact-head CI and governed landing.
- Cleanup: pending verified merge.

## Residual items

- Post-merge live acceptance must reach PR #628 and the fresh #627 merge on landed `kis-op` without checkpoint manipulation before Work/GitHub issue #641 is closed.
