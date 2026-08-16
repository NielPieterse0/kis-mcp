# Closeout: Work Management View Filter Invariant

## Implemented scope

- Corrected canonical views `04`, `05`, `06`, `09`, `10`, and `11` so every one of the 12 view filters explicitly constrains `Status` to current command-plane lifecycle values.
- Kept purpose-specific lifecycle subsets narrow where required; `05 Specification Slices` begins at `Proposed`, while broad historical/specialist views enumerate all canonical statuses.
- Added load-time validation for the canonical default 12-view manifest: `Status` must exist as a non-empty single-select, every view must contain exactly one `status:` qualifier, and status values must be non-empty, unique, well-formed, and canonical.
- Preserved generic smaller manifest fixtures without a `Status` field.
- Reconciled programme metadata to identify change 166 as pending live acceptance instead of retaining stale change-162/#270-reopened wording.

## Validation evidence

- Red regression: the new all-12 lifecycle-filter test failed first on `04 Roadmap`, proving the previous manifest omitted a Status constraint.
- Focused schema tests: 14/14 passed after the initial correction.
- Final affected suite after review fixes: 243/243 passed across `tests/work_management` and `tests/providers/github/projects/test_schema_commissioning.py`.
- Ruff: changed Python/test files pass.
- Python compilation: `src/kis_mcp/work_management/schema.py` passes.
- `git diff --check`: passed.
- `pwsh -NoProfile -File scripts/change-workflow.ps1 check`: passed; all changed paths are inside change 166 ownership.

## Review

- Initial code-quality review found premature programme completion metadata (high) and permissive empty status-list parsing (medium); both were corrected.
- Initial API-contract review found ambiguous Status-less canonical handling (medium); it was corrected.
- The first immutable commit API review then found that `default + 12 views` was an incidental discriminator (medium). Canonical validation is now selected by the configured canonical manifest path, requires exactly 12 views plus `Status`, and explicit alternate manifests retain generic behavior.
- Final full-range re-reviews remain required after the corrective commit.

## Git and merge

- Branch: `change/166-work-management-view-filter-invariant`.
- Worktree: `.work/worktrees/166-work-management-view-filter-invariant`.
- Commit / PR / exact-head Actions / merge: pending immutable commit review and publication.
- Cleanup: pending verified merge and live recommissioning.

## Residual acceptance gates

- Review the immutable final commit, then publish and merge only that exact head after provider-native exact-head Actions succeeds.
- Run the corrected manifest on a landed/restarted KIS runtime; require all 12 saved views behaviorally verified, zero view mismatches/unverified views, and an empty schema plan.
- Reconcile only evidence-backed legacy lifecycle drift; do not bulk-map ambiguous `Todo` backlog.
- Replace the temporary pending programme state with the stable dynamic-readiness state, reconcile #270/#142 evidence, and clean the change only after live acceptance.