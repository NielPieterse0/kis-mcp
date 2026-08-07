# Closeout: Discover Git Evidence Resilience

## Status

Active. Governance artifacts were registered before implementation edits.

## Baseline evidence

- Live `inspect_project` and `inspect_change` returned `GIT_METADATA_TOO_LARGE` for `C:\Projects\kis-mcp`.
- `settings.discover.limits.git_metadata_max_bytes` is 4,096.
- Current repository `.git/index` size is 109,520 bytes; `.git/config` is 1,085 bytes.
- Source inspection shows `validate_git_metadata_graph` reads/size-checks the opaque index through `_validate_regular_file`, even though Discover does not parse the index itself.

## Worktree provenance

The canonical `change-workflow.ps1 new` path could not safely create this slice from the intended current remote base because local `main` was clean but ahead 6 / behind 4 relative to `origin/main`. Under the documented manual-worktree emergency exception, the worktree was created at `.work/worktrees/062-discover-git-evidence` from `origin/main`, branch `change/062-discover-git-evidence`, without modifying the primary checkout. Governance validation is required before implementation edits.

## Verification

- RED: `test_large_git_index_remains_available_for_repository_and_linked_worktree` failed with `summary.available is False` and `GIT_METADATA_TOO_LARGE`; `pytest_exit=1`.
- GREEN: the same regression passed after the index-validation correction; `pytest_exit=0`.
- Full `tests/discover/test_git_reader.py`: 11 passed.
- Full `tests/discover` plus `tests/architecture/test_modularity_boundaries.py` and `tests/architecture/test_capability_composition_boundaries.py`: passed with one existing skip; `pytest_exit=0`.
- `pwsh -NoProfile -File scripts/change-workflow.ps1 check`: passed with all changed paths inside the declared claim.
- `git diff --check`: passed.
- Review: no blocking correctness, policy, scope, or simplification findings. The opaque index remains canonicalized and must be a regular unlinked file; text/control metadata keeps the configured byte cap.
- `pwsh -NoProfile -File scripts/verify.ps1` was attempted through the fallback command connector twice but exceeded its synchronous execution window before returning a result. No full-verifier pass is claimed from those attempts. Exact-head repository CI/full verification is required before merge.

## Landing

Pending exact-head commit, push, PR, CI/full verification, merge, and governed closeout.
