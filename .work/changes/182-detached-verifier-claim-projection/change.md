# Change: Detached Verifier Claim Projection

- **Change ID**: `182-detached-verifier-claim-projection`
- **Risk Profile**: lean

## Outcome

Make exact detached local verification resolve the single governed PR claim from the merge-base diff so landed schema-v3+ claims are projected closed without weakening ambiguous detached fail-closed behavior.

## Scope and acceptance

- Implement only the paths declared in `scope.json`.
- Detached exact verification may infer a branch only from one unambiguous changed schema-v3+ active/ready scope record whose change ID and branch agree with its path.
- Missing, malformed, mismatched, or multiple changed scope records remain fail-closed.

## Implementation and verification

- Implementation notes: Detached verification projects only the single governed claim changed between merge-base and HEAD; ordinary branch/GitHub identity paths are unchanged.
- Focused checks: `tests/test_repository_scope.py` passes with explicit single-claim, ambiguous-claim, malformed JSON, unsupported schema, and missing-branch coverage.
- Review findings: Exact-diff API-contract review is clean. Code-quality review requested explicit malformed-scope coverage; that regression was added. Low-severity logging/deduplication suggestions were not adopted because fail-closed behavior is intentional and `git diff --name-only` supplies unique paths.
- Residual risk: Exact-head canonical verification and refreshed post-fix reviews remain required before merge.
- Closeout state: Active; PR #345 must be reconciled to the amended head and re-gated.
