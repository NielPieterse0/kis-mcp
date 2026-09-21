# Closeout: Historical Change Recovery Maze

## Implemented scope

- Live linked worktree scope records now override stale base copies for the same change ID.
- Schema-v3+ landed base claims release once no live linked worktree remains, even when a preserved historical branch later gained residual commits.
- Added regressions for live override, retired-worktree release, and same-path governed follow-up creation.

## Validation evidence

- Focused regressions: 2 passed via `scripts/test.ps1`.
- Governance/capability suite: 72 passed across `tests/test_change_governance.py` and `tests/capabilities/test_governed_change.py`.
- Diff scope check: `pwsh -File scripts/change-workflow.ps1 check` passed.
- Repository verification: deferred to canonical exact-head pull-request CI per repository contract.

## Review

- NVIDIA qualified reviewer routes failed with malformed responses; explicit Codex fallback completed.
- Codex raised one high finding that preserved branch-only residual commits should keep a retired claim active.
- Resolution: rejected as contrary to REQ-002/REQ-003 and the defect being fixed. Residual commits remain protected while a live worktree exists; once that worktree is retired, the already-landed historical claim must not reacquire ownership solely because a preserved branch advanced.

## Git and merge

- Branch: `change/718-historical-change-recovery-maze`
- Worktree: `.work/worktrees/718-historical-change-recovery-maze`
- Commit:
- Pull request or merge:
- Cleanup:

## Residual items

-
