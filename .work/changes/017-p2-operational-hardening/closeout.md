# P2 Operational Hardening Closeout

## Status

Implementation and repository verification complete. Publication is pending the final commit and PR creation.

## Implemented scope

- Discover compaction now treats retained `run_verification` handoffs and their declarations as one semantic unit. Orphaned verification references fail with `DISCOVER_VERIFICATION_HANDOFF_INVALID` rather than producing an internally inconsistent response.
- Quarantine payload hashing now uses bounded iterative traversal with explicit entry, byte, depth, and duration limits, stable limit codes, and diagnostic counters. Symlinks and reparse points remain unhashed as targets and are not followed.
- Quarantine record listing retains only the requested newest candidates and validates only that bounded result window instead of materializing and validating the complete store.
- The deployment model is now explicitly `source-checkout-only`. Default runtime configuration fails with `KIS_MCP_SOURCE_CHECKOUT_REQUIRED` outside a checkout containing the canonical settings and policy JSON.
- Supabase provider descriptor construction is explicit and no longer loads provider configuration during module import.
- Historical claims `009-supabase-mcp-provider` and `014-provider-runtime-composition` were closed because their PRs are already merged and their stale active ownership blocked governance validation.

## Verification

- Baseline focused tests: 35 passed.
- Red-green regressions reproduced the verification orphan, unbounded quarantine traversal/listing behavior, unsupported distribution model, and import-time Supabase configuration load.
- Final focused slice: 50 passed.
- `git diff --cached --check`: passed.
- `pwsh -NoProfile -File scripts/change-workflow.ps1 check`: passed with 22 declared changed paths.
- `pwsh -NoProfile -File scripts/verify.ps1`: passed.
  - 406 tests passed.
  - 2 expected skips.
  - 66 Python files passed syntax validation.
  - 12 governance claims passed.
  - Configuration, dependency, interpreter, and exact HR-001/HR-002/HR-003 checks passed.

## Remaining P2 integration dependencies

The attached review contains eight P2 findings. This isolated slice directly closes verification compaction, quarantine bounds/listing, and the distribution/import-time configuration finding.

- `013-startup-hardening`, PR #17, owns transactional tunnel setup and live-readiness sequencing.
- `016-discover-response-hardening` owns the response schema, deterministic scanner cutoff, and Python diagnostic truncation/evidence findings; its worktree remains uncommitted at this closeout point.
- The exact omitted network-client resolver finding is not present in the clean `015-p1-boundary-hardening` PR and still requires a non-overlapping dependent follow-up after that command-intent branch lands.

This branch must not be represented as closing those concurrent or still-unclaimed findings until their exact heads are integrated and reverified.

## Governance exception and recovery

Normal `change-workflow new` creation initially failed because the repository scanner recursively read copied historical claims from linked worktrees. The branch and worktree were created through the documented emergency path, with scope artifacts registered before implementation edits. Final governance validation passed after closing the two genuinely stale merged claims.

An accidental repository-local `.venv` created by an initial unpinned test attempt was quarantined recoverably as operation `f964bb9352c643b3889db789f54a4231`. The locked external environment was used for final verification.

## Rollback

The change is isolated on `change/017-p2-operational-hardening`. Before merge, rollback is removal of the unmerged branch/worktree through the approved recoverable workflow. No policy rule, credential, external system, provider authorization, or canonical settings value is changed by this slice.
