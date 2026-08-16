# Closeout: Github Mutation Timeout Receipts

## Implemented scope

- Added stable deterministic operation identities and the five-state `not_started | in_progress | applied | failed | unknown` receipt vocabulary to registered GitHub publication, reconciliation, PR creation, and the pre-review completion coordinator.
- Added bounded `deadline_ms` handling with aggregate completion timing, nested remaining-budget propagation, reconciliation reserve, elapsed time, and per-stage timing evidence.
- Added read-only `status_only` / `reconcile_only` recovery paths so ambiguous outcomes are resolved from exact GitHub branch/PR authority before retrying.
- Made branch publication and PR creation acknowledgement-loss safe across command timeout, post-mutation verification loss, malformed PR-create acknowledgement, and other registered command failures without repeating the mutation.
- Made PR duplicate recovery inspect paginated head/base history and accept recovery only when exactly one total matching history entry is the exact open non-draft PR.
- Replaced the temporary thread-based injected-runner timeout wrapper with an explicit timeout-aware runner contract so a returned receipt never leaves a mutating background runner alive; native `subprocess.TimeoutExpired` from an injected runner is normalized into the same reconciliation path.
- Preserved the stateless boundary required by #278: receipts are exposed/queryable but no durable receipt store was introduced.
- Updated operator documentation and compatibility tests for the new receipt/deadline contract.

## Validation evidence

- Focused #274 surface: 63 tests passed across `tests/projects/test_github_exact.py`, `tests/capabilities/test_registered_commit_workflow.py`, `tests/workflows/completion/test_completion_service.py`, `tests/workflows/completion/test_completion_tools.py`, and `tests/workflows/test_registered_commit_publication.py`.
- Exact changed-Python Ruff checks: passed.
- Python compilation over `src` and `tests`: passed.
- `git diff --check HEAD`: passed.
- `pwsh -NoProfile -File scripts/change-workflow.ps1 check`: passed with all 15 changed paths inside change 161 ownership.
- Canonical full repository verification is intentionally deferred to provider-native exact-head pull-request CI per repository authority; it must pass before merge.

## Review

- Earlier low-level review findings in #274 scope were resolved: post-push verification acknowledgement loss, PR-create acknowledgement loss, non-timeout registered command ambiguity, incomplete PR-history pagination, and exact-plus-conflicting historical PR recovery.
- Architecture review identified the injected-runner deadline seam. The initial thread wrapper was rejected because it could return while a mutating runner remained alive; the final implementation instead requires deadline-aware injected runners and contains no background mutation thread.
- Final manual exact-diff architecture fallback found one seam-specific edge: a timeout-aware injected subprocess runner could raise native `subprocess.TimeoutExpired` instead of `ToolError`. `_run` now normalizes that exception, and a regression proves remote authority is reconciled without a second push.
- Automated specialist re-review could not consume the complete 15-file evidence atomically (`AGENT_EVIDENCE_FILES_OMITTED` / incomplete evidence), so it was not treated as a pass. The required exact-diff manual fallback covered deadline propagation, receipt state transitions, exact GitHub authority, retry safety, stateless ownership, and the public completion/registered-GitHub contract; no remaining blocking finding was identified.
- Ruff additionally exposed an exact duplicate test/helper definition inside the claimed test file; the duplicate was removed and the full focused surface rerun green.

## Git and merge

- Branch: `change/161-github-mutation-timeout-receipts`
- Worktree: `.work/worktrees/161-github-mutation-timeout-receipts`
- Commit: pending exact reviewed-tree commit.
- Pull request / exact-head Actions / merge: pending.
- Cleanup: pending verified merge.

## Residual items

- Publish the exact reviewed commit through the governed registered-GitHub path.
- Require provider-native GitHub Actions success for the exact PR head, then merge only that head.
- Refresh registered default-branch truth, close/reconcile #274, delete the verified remote review branch, and safely clean the merged worktree.
- #278 remains the authority for any future durable mutation-receipt persistence; this change deliberately does not create one.
