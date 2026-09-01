# Change: Repository-Scoped Work Projection

- **Change ID**: `190-repository-scoped-work-projection`
- **Parent**: Change 186 / issue #356
- **Landed pull request**: #371
- **Reviewed/verified head**: `9090479d31cedbb09c899ddaf6e718c26c89e5df`
- **Merge commit**: `20fb433d78ddd4e85f0864e2c84f9535f11f2a3f`
- **Merged at**: `2026-08-18T10:16:15Z`

## Outcome

Restore repository-scoped Work projection on the reconstructed post-Actions baseline while keeping GitHub Actions as the canonical exact-head repository verification authority.

## Reconciled landed evidence

PR #371 (`change/190-repository-scoped-work-projection` → `main`) was merged from exact head `9090479d31cedbb09c899ddaf6e718c26c89e5df` as merge commit `20fb433d78ddd4e85f0864e2c84f9535f11f2a3f`.

The historical zero-byte copy of this record was an evidence defect explicitly carried by issue #367. It did not change the already-landed implementation or Git history. Issue #622 / Change 616 repairs only the missing durable change record from authoritative Git/GitHub facts; it does not recreate or rewrite Change 190 implementation history.

## Closeout

- Landed implementation identity is preserved by PR #371 and the exact head/merge pair above.
- Historical branch/worktree closeout is not inferred from this repaired record beyond the facts independently observable from current repository state.
- The repaired record is part of the final #491/#503 legacy reconstruction reconciliation.