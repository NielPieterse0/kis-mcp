# Closeout: Command Plane Live Commissioning Fixes

## Implemented scope

- Corrected GitHub Project item normalization so metadata-only empty field entries become `None` instead of their field names.
- Preserved direct provider scalar shapes (`text`, `number`, `date`, `title`, and iteration titles).
- Added repository-owned `Blocked By` as a text field, raising the desired Project schema from 24 to 25 fields while retaining 12 views.
- Updated `SPEC.md` and `docs/OPERATIONS.md` to document the dependency-evidence and empty-value contracts.

## Validation evidence

- Red evidence: the new empty-value adapter regression returned `Execution Owner` instead of `None`; the new schema regression raised `KeyError: Blocked By`.
- Focused/affected checks: 38 tests passed across adapter, commissioner, command settings/service/queue, and schema planning after the intended schema-count updates.
- Canonical verification: `scripts/verify.ps1` passed on the corrected worktree package; full pytest, Python syntax, configuration, interpreter, dependency, line-ending, and change-governance checks were green.
- Diff scope: `git diff --check` and `scripts/change-workflow.ps1 check` passed.

## Review

- Code-quality: zero findings.
- API contracts: zero findings.
- Safety/security: zero findings.
- Architecture: zero findings.
- Backend: NVIDIA NIM `nvidia/nemotron-3-super-120b-a12b` for all four final reviews.

## Git and merge

- Branch: `change/155-command-plane-live-commissioning-fixes`
- Worktree: `.work/worktrees/155-command-plane-live-commissioning-fixes`
- Base: `5a3f09228b84f50f077c7acd9ba5acd24faffad2`
- Commit: pending final exact-tree verification and commit.
- Pull request / merge: pending exact-head publication and provider-native CI.
- Cleanup: pending merge plus live commissioning.

## Residual items

- Land the exact reviewed change through the governed PR path.
- Recommission Project #1 additively to create `Blocked By`, then verify 25 fields / 12 views with an empty repair plan.
- Run live queue/claim/release/hold/defer/transition/completion smoke against #142 and close the issue only after acceptance passes.
