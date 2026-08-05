# Closeout: Discover Change Targets

## Implemented scope

- Generalized `InspectChangeRequest` and `ChangeIdentity` for `working_tree`, `staged`, `commit`, `range`, and `branch` sources with strict target-shape and conservative Git-ref validation.
- Added deterministic target inventory, fixed direct-argument Git templates, rename/copy parsing, timeout/error/truncation classification, and bounded file retention.
- Added `GitChangeReader` while preserving the existing `GitReader` as the sole subprocess adapter.
- Preserved the original working-tree service path and additive schema compatibility.
- Added typed Work verification handoffs derived from changed path categories while retaining explicit symbol and dependant-impact unknowns.
- Added strict draft-2020-12 request and generalized response schemas.

## Validation evidence

- Baseline full repository verification passed before implementation: 529 tests, 2 expected skips, 76 Python files.
- Affected tests passed: 19 target, service, and schema tests.
- Full Discover suite passed: 133 tests with 1 expected skip.
- `pwsh -NoProfile -File .\scripts\change-workflow.ps1 check` passed with all changed paths inside the declared claim.
- `git diff --check` passed.
- Final `pwsh -NoProfile -File .\scripts\verify.ps1` passed: 539 tests, 2 expected skips, 78 Python files, governance, line endings, dependencies, configuration, interpreter, and exact three-rule checks.

## Review

- Whole-diff review covered request validation, Git argument interpretation, metadata and boundary handling, timeout/failure paths, deterministic ordering/fingerprints, schema compatibility, architecture confinement, and verification handoff behavior.
- One architecture issue was found and repaired: subprocess timeout classification was moved behind the existing `git_reader.py` adapter boundary.
- One compatibility issue was found and repaired: readers supporting both APIs now preserve the original working-tree inventory path and fingerprint behavior.
- No unresolved P0–P2 findings remain.

## Git and merge

- Branch: `change/027-discover-change-targets`
- Worktree: `.work/worktrees/027-discover-change-targets`
- Commit: pending publication
- Pull request: pending publication
- Cleanup: pending merge

## Residual items

- Public MCP registration for the generalized request remains intentionally deferred to the Discover integration slice.
- Remote pull-request evidence, semantic symbol impact, and bounded dependant graphs remain later roadmap slices and are reported explicitly rather than inferred.
