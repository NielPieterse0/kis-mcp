# Change: Pr Create Reconcile Canonical

- **Change ID**: `614-pr-create-reconcile-canonical`
- **Risk Profile**: lean

## Outcome

Reconcile successful registered PR creation against canonical normalized request state without false conflicts or duplicate mutation.

## Scope and acceptance

- Canonicalize registered PR bodies once for request identity and GitHub comparison.
- Treat CRLF/CR versus LF transport normalization as equivalent without weakening title/head/base checks.
- Preserve fail-closed behavior for genuine metadata conflicts and prevent duplicate PR mutation.

## Implementation and verification

- Implementation notes: added one canonical PR-body representation that combines closing-reference neutralization with newline normalization; exact-history and post-create verification compare against that representation.
- Focused checks: managed `uv` environment `tests/projects/test_github_exact.py` — 21 passed; change scope check and `git diff --check` passed.
- Review findings: exact-diff review found no blocker; metadata-drift regression remains fail-closed.
- Residual risk: only newline representation is canonicalized; materially different body text remains conflicting.
- Closeout state: implementation and local affected verification complete; publication/Actions/merge/Work closeout pending.
