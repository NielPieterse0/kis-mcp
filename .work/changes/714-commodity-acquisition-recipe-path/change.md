# Change: Commodity Acquisition Recipe Path

- **Change ID**: `714-commodity-acquisition-recipe-path`
- **Risk Profile**: lean

## Outcome

Repair Commodity registered external acquisition after repository consolidation by updating KIS to resolve immutable Commodity recipes from data/acquisition-recipes, without widening acquisition authority.

## Scope and acceptance

- Resolve Commodity registered acquisition recipes from canonical `data/acquisition-recipes` for both authorized profiles.
- Preserve every existing approval, recipe-prefix, parameter, provider-profile, credential, and network boundary unchanged.
- Prove the shipped settings no longer depend on retired `config/acquisition-recipes`.
- Confirm registered acquisition can resolve the current Commodity recipe after the repair is landed.

## Implementation and verification

- Implementation notes: changed only the two Commodity `recipe_directory` values and added a shipped-settings regression test.
- Focused checks: regression test failed before the settings repair and passed after it; all 11 `tests/acquisition` tests pass; `scripts/change-workflow.ps1 check` passes.
- Review findings: no mandatory specialist review is configured for this Small migration-only change; exact-head CI remains the publication gate.
- Residual risk: the running KIS process may require settings reload/restart before live acquisition reflects the landed path.
- Closeout state: implementation in progress.
