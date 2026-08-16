# Closeout: Work Management View Filter Invariant

## Implemented scope

- Corrected canonical views `04`, `05`, `06`, `09`, `10`, and `11` so every one of the 12 view filters explicitly constrains `Status` to current command-plane lifecycle values.
- Kept purpose-specific lifecycle subsets narrow where required; `05 Specification Slices` begins at `Proposed`, while broad historical/specialist views enumerate all canonical statuses.
- Added fail-closed validation for the configured canonical manifest: exactly 12 views, a non-empty current `Status` single-select, exactly one `status:` qualifier per view, and non-empty, unique, canonical status values.
- Preserved explicitly supplied alternate manifests as generic parser inputs.

## Local verification and review

- Red regression failed first on `04 Roadmap`, proving the previous manifest omitted a Status constraint.
- Final affected suite: **243/243 passed** across `tests/work_management` and `tests/providers/github/projects/test_schema_commissioning.py`.
- Ruff, Python compilation, `git diff --check`, and `scripts/change-workflow.ps1 check` passed.
- Initial reviews found and drove fixes for premature programme completion state, permissive empty status-list parsing, missing canonical `Status` handling, and an incidental `default + 12 views` discriminator.
- Final full-range code-quality and API-contract reviews on `03c677d…bd1386f` completed with zero findings.

## Delivery evidence

- Final local source: `bd1386fe93cfc0719029d0fae69536a24eef5412`.
- Registered tree-equivalent review head: `fa9a5e67fed548ca3c311200f057abc763f50623`.
- PR #301 passed Canonical Verification run `31934864345` / `Verify exact head` on that exact head.
- PR #301 merged as `1e51544b4d4e43ad90f890bfbb622f18c45519c7`.
## Live commissioning evidence

- Fresh `kis-dev` server instance `ec259d1d62f44cd7ac0344a5f07deb55` ran source revision `1e51544b4d4e43ad90f890bfbb622f18c45519c7`.
- Pre-repair status correctly returned `ready=false`, `views_ready=false`, filter mismatches for `04`, `05`, `06`, `09`, `10`, and `11`, and `12 Completed` behaviorally unverified.
- The bounded registered-Project commissioner updated exactly those six existing views in place, created no views, and re-read all 12 canonical views as `verified=true` with zero mismatches.
- Independent post-repair status returned `ready=true`, `fields_ready=true`, `views_ready=true`, with no missing, unverified, or mismatched views.
- Independent schema plan returned `ready=true`, `automatic_ready=true`, `actions=[]`, `unverified_views=[]`.
- Current legacy-state read contains zero `In Progress` items. Seventeen remaining `Todo` records are ambiguous backlog and were intentionally not bulk-remapped without lifecycle evidence; canonical filters exclude legacy values.
- #270 and #142 carry the final dated acceptance evidence. The #270 Project item is `Done` / `Complete` / `Passed` with Change ID `166-work-management-view-filter-invariant` and Authority Revision `1e51544b4d4e43ad90f890bfbb622f18c45519c7`.

## Cleanup

- Remote review branch `change/166-work-management-view-filter-invariant` was deleted only at exact head `fa9a5e67fed548ca3c311200f057abc763f50623`.
- Local cleanup completed as `tree_equivalent_reachable`; branch/worktree were removed non-forcibly.
- Recovery ref `refs/kis-recovery/cleanup/166-work-management-view-filter-invariant` preserves original local head `bd1386fe93cfc0719029d0fae69536a24eef5412`.
- This historical record is reconciled into current programme/root authority by change `159-work-management-authority-reconcile`.