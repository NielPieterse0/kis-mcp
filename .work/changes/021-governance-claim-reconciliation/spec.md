# Governance Claim Reconciliation

- **Change ID**: `021-governance-claim-reconciliation`
- **Outcome**: Reconcile stale merged claims and retain explicit template exclusion evidence.

## Requirements

1. Mark only merged claims still reported as active on `origin/main` as closed.
2. Preserve already-closed records unchanged.
3. Prove underscore-prefixed template directories are excluded from claim discovery.
4. Do not modify settings, runtime code, other hygiene items, or active development claims.

## Acceptance evidence

- Merge ancestry confirms each changed claim is included in `origin/main`.
- Focused governance tests pass.
- Change scope and whitespace checks pass.
