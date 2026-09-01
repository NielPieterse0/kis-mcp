# Closeout: Review Candidate Identity

## Implemented scope

- Added validated substantive review closure and directly affected correction re-review selection.
- Added candidate v2 identity binding for source commit/tree, policy/runtime fingerprints, endpoint, Work/contract/server/process identity.
- Added exact candidate reuse/drift rejection and deterministic effect-aware automatic live scenarios.
- Integrated only the coordinated #587 portions of `once_through/tools.py`.

## Validation evidence

- Focused checks: `38 passed` across the new #587 suite plus existing `test_once_through.py`.
- Ruff: new modules/tests and `tools.py` import ordering pass targeted lint.
- Diff scope check: pending final rerun after lifecycle record completion.
- Repository verification: delegated to canonical exact-head PR CI per `AGENTS.md`.

## Review

- Findings: pending independent review.
- Resolutions: pending.

## Git and merge

- Branch: `change/610-review-candidate-identity`
- Worktree: `.work/worktrees/610-review-candidate-identity`
- Commit: pending.
- Pull request or merge: pending.
- Cleanup: pending.

## Residual items

- #588 and #569 remain separate parallel work; no owned paths were absorbed.
