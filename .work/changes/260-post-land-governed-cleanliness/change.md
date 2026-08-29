# Change: Post-Land Governed Cleanliness

- **Change ID**: `260-post-land-governed-cleanliness`
- **Issue**: `#580`
- **Parent programme**: `#571`

## Outcome

Allow the detached post-land `kis-dev` restart worker to ignore only the known generated verification/review evidence path while preserving fail-closed behavior for every other repository change.

## Implementation

- Added `Test-KisPrimaryGovernedDirty` to classify raw Git status before restart.
- Untracked `.work/programmes/verification-review-evidence/**` is non-blocking generated evidence.
- Tracked changes and every other untracked path remain blocking.
- `kis-op` lifecycle is unchanged.

## Verification

- `uv run python -m pytest tests/projects/test_post_land_restart.py -q`: 37 passed.
- `pwsh -File scripts/change-workflow.ps1 check`: pass.
- `git diff --check`: pass.
- KIS code-quality review: no actionable findings.

## Recovery

Revert this change to restore the prior all-dirt restart guard. The preserved pre-fix evidence is quarantined under `.temp/kis/quarantine/verification-review-evidence-pre-580` in primary main.
