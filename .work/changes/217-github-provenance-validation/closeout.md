# Closeout: GitHub Provenance Validation

## Implemented scope

- Added strict provider-verified GitHub issue/PR/head/merge provenance evidence.
- Froze verified provenance into durable worker execution state at packet-backed admission.
- Propagated immutable provenance through worker handoff, reconciliation, integration, delivery, and schemas while retaining compatibility for older v3/v1 artifacts.
- Added deterministic mismatch/quarantine behavior and regression coverage.

## Validation evidence

- Focused coordinator regression suite: 62 tests passed.
- New-file/export Ruff checks: passed after 5 direct Change 217 fixes.
- `git diff --check`: passed.
- `pwsh -File scripts/change-workflow.ps1 check`: passed.
- Broad coordinator Ruff sweep still reports 58 pre-existing findings outside the bounded Change 217 cleanup.

## Review

- API-contract review first found three real defects: same-version schema compatibility, caller-selected handoff provenance, and runtime/schema unknown-key drift; all were corrected.
- Architecture review then found late packet ownership of provenance; corrected by freezing provenance into durable `WorkerExecution` admission state and adding a regression proving later packet provenance cannot replace it.
- Subsequent automated architecture/API-contract/code-quality retries exhausted reviewer runtime deadlines; the tool required manual exact-diff fallback.
- Manual exact-diff fallback found no unresolved Change 217 defect after the fixes and current green tests/checks.

## PR exact-head CI follow-up

- PR #440 exact head `284c85204770215ae5aa5dfed06388ff6c214d5d` failed canonical verification on two stale Change 217 test expectations only.
- Updated the coordinator package inventory to include `provenance.py`.
- Updated packet handoff-field coverage to preserve the intended distinction: historical worker-handoff v3 artifacts may omit `external_provenance`, while newly issued Change 217 packets require it.
- Exact failing tests now pass; full `tests/workflows/coordinator` passes (116 tests), `git diff --check` passes, and `pwsh -File scripts/change-workflow.ps1 check` passes.

## Git and merge

- Branch: `change/217-github-provenance-validation`
- Worktree: `.work/worktrees/217-github-provenance-validation`
- Implementation commit: `88c6d0d4d5c99592427b8749fca83b149decdb2c`
- Pull request: #440 open; merge pending
- Cleanup: pending

## Residual items

- Exact-head GitHub Actions, Work Management merge-readiness, merge, reconciliation, and governed cleanup remain required.