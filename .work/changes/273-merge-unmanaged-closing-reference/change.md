# Change: Merge Unmanaged Closing Reference

- **Change ID**: `273-merge-unmanaged-closing-reference`
- **Risk Profile**: lean

## Outcome

Prevent late registered-merge failures by normalizing GitHub issue-closing keywords in generated reviewable pull-request prose while preserving the merge-time guard.

## Scope and acceptance

- Implement only the paths declared in `scope.json`.
- Generated reviewable PR summaries must convert GitHub closing-keyword references such as `Fixes #606` into non-closing references before PR creation.
- Ordinary issue references remain unchanged.
- The registered merge operation retains its existing fail-closed closing-reference guard as defense-in-depth.
- Direct low-level PR creation remains explicit caller-controlled behavior; this change fixes the canonical completion path that generated the late failure.

## Implementation and verification

- Implementation notes: added shared closing-reference normalization beside the existing registered merge detector; canonical completion-generated PR summary prose now converts only GitHub closing-keyword references to `Related:` references before PR creation. The merge-time block remains unchanged.
- Focused checks: 128 tests passed across `tests/workflows/test_registered_commit_publication.py` and `tests/workflows/completion/test_completion_service.py`; `git diff --check` and `scripts/change-workflow.ps1 check` are clean.
- Review findings: configured NVIDIA code-quality routes were unavailable/unusable, requiring exact-diff manual fallback. Manual review found no blocking correctness, regression, or architecture issue.
- Residual risk: source commit messages containing GitHub closing keywords remain intentionally blocked at merge; this change addresses generated PR prose only and does not weaken terminal-authority defense-in-depth.
- Closeout state: implementation and local affected verification are complete; immutable publication, exact-head CI, landing, issue close, and cleanup remain.
