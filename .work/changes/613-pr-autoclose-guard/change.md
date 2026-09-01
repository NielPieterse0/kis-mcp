# Change: Pr Autoclose Guard

- **Change ID**: `613-pr-autoclose-guard`
- **Risk Profile**: lean

## Outcome

Block implicit GitHub auto-close keywords in managed registered PR creation while preserving neutral references and deterministic retry reconciliation.

## Scope and acceptance

- Registered PR creation neutralizes GitHub closing keywords before operation identity, reconciliation, creation, and post-create verification.
- Same-repository and qualified cross-repository references, including mixed case, become neutral `Related:` references.
- Existing neutral references and retry/exact-request semantics remain unchanged.

## Implementation and verification

- Implementation notes: reuse the existing shared `normalize_issue_closing_references` function at the registered PR boundary; the normalized body is the sole body used for operation identity, history matching, `gh pr create`, and verification.
- Focused checks: managed `uv` environment `tests/projects/test_github_exact.py` — 20 passed; `scripts/change-workflow.ps1 check` passed; `git diff --check` passed.
- Review findings: exact-diff/manual review found no blocking issue. Configured specialist review and composite change workflow both returned upstream 502 before producing findings. Repository-wide Ruff on the two changed files reports three pre-existing diagnostics in unchanged lines of `github_exact.py`; none are introduced by this diff.
- Residual risk: the normalization intentionally preserves issue references as `Related:` text; a future explicit auto-close feature would require a separately approved/hardened contract rather than bypassing this default.
- Closeout state: implementation and affected local verification complete; publication/Actions/merge/Work closeout pending.
