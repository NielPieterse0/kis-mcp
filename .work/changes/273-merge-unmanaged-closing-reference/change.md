# Change: Merge Unmanaged Closing Reference

- **Change ID**: `273-merge-unmanaged-closing-reference`
- **Risk Profile**: `external_action`

## Outcome

Allow registered merge closeout for confirmed unmanaged GitHub issue-closing references while preserving Work lifecycle protection for managed issues and failing closed when management status is ambiguous or unavailable.

## Scope and acceptance

- Implement only the paths declared in `scope.json`.
- Parse closing references from PR bodies and commit messages without changing ordinary references.
- For every closing reference, query authoritative GitHub Project membership against the registered Work project binding.
- Confirmed unmanaged issues may proceed through the registered exact-head merge path.
- Work-managed issues remain blocked before merge mutation.
- Missing project binding, provider failure, malformed lookup evidence, missing issue identity, or paginated/incomplete membership evidence fails closed.
- Existing approval, exact-head, merge-method, state, and post-land guards remain intact.

## Implementation and verification

- Implementation notes: merge-time closing references are now classified against the configured Work project instead of being rejected categorically. The earlier generated-PR prose normalization approach was removed because it addressed the symptom rather than the required invariant.
- Focused checks: `tests/workflows/test_registered_commit_publication.py` passes with third-party pytest plugin autoload disabled to avoid the unrelated unmanaged user-profile plugin conflict.
- Review findings: pending governed specialist review.
- Residual risk: GitHub Project membership is bounded to the first 100 project items; any pagination is treated as unverifiable and blocks merge rather than guessing.
- Closeout state: implementation is in progress; governed verification, review closure, immutable publication, exact-head CI, landing, issue close, and cleanup remain.
