# Change: Local Verifier Claim Projection

- **Change ID**: `139-local-verifier-claim-projection`
- **Risk Profile**: lean

## Outcome

Make canonical local repository verification project landed historical schema-v3+ claims closed by resolving the current Git branch when GITHUB_HEAD_REF is absent, while preserving PR-head semantics.

## Scope and acceptance

- `scripts/verify.py` must prefer `GITHUB_HEAD_REF` for pull-request CI, then `GITHUB_REF_NAME` for branch CI, then the current local symbolic Git branch.
- Local verification in a governed change worktree must preserve that current claim while projecting other schema-v3+ landed historical claims closed.
- Detached/no-branch execution may return no branch and retain the existing fail-closed behavior.
- No historical change metadata is edited merely to suppress false overlap findings.

## Implementation and verification

- Implementation notes: added `_verification_branch()` and routed change-governance projection through it.
- RED: focused repository-scope tests failed because `_verification_branch` did not exist.
- GREEN: `tests/test_repository_scope.py` passes 17/17; Ruff passes; change-scope check passes.
- Review findings: independent code-quality review completed with no findings.
- Canonical verification: full repository verifier passed, including change governance and pytest.
- Residual risk: branch-name detection is deliberately read-only and falls back to existing fail-closed semantics when Git cannot identify a branch.
- Closeout state: implementation and local verification complete; exact-head CI/landing pending.
