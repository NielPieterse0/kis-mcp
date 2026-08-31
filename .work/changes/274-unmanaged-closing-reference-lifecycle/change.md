# Change: Unmanaged Closing Reference Lifecycle

- **Change ID**: `274-unmanaged-closing-reference-lifecycle`
- **Risk Profile**: lean

## Outcome

Allow registered merge closeout for confirmed unmanaged issue-closing references while preserving managed Work lifecycle protection and fail-closed lookup semantics.

## Scope and acceptance

- Work-managed referenced issues remain protected from registered merge closeout that would bypass Work lifecycle completion.
- Confirmed unmanaged referenced issues may use ordinary GitHub closing references.
- Ambiguous lookup, incomplete evidence, pagination, or provider failure blocks merge before mutation.
- Pull-request bodies and commit messages are both classified.
- Existing exact-head, approval, merge-state, and closing-reference normalization compatibility behavior remains intact.

## Implementation and verification

- Implementation notes: classify every closing reference against the configured Work project at registered merge time; allow only confirmed unmanaged references.
- Focused checks: pending final exact-change run.
- Review findings: pending final exact-commit review.
- Residual risk: Work membership lookup is intentionally fail-closed when provider evidence cannot prove unmanaged status.
- Closeout state: implementation in progress.
