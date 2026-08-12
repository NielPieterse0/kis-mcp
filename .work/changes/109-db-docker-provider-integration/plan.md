# DBHub and Docker Hub Provider Integration Plan

## Status

Approved for implementation by the operator on 2026-08-12. Change 108 is closed and 109 is rebased on current GitHub-synchronized `main`.

## Slice 1 — Contracts and routing

1. Extend provider boundary contracts with `source_aware_connector`.
2. Extend strict project contracts/schema/settings with `databases` and `dockerhub`.
3. Register only College `results\\college.db`; add no invented Docker Hub/project binding.
4. Extend provider-runtime JSON/schema with `dbhub` and `dockerhub` namespaces.

## Slice 2 — DBHub provider kernel

5. Add strict pinned DBHub settings and installation/readiness contracts.
6. Build one isolated child proxy per registered DB binding and deterministic nested namespace.
7. Generate per-binding runtime TOML beneath KIS state with readonly SQL/max-row policy and no resolved secrets.
8. Predeclare stable per-binding capability metadata/effects before generic runtime augmentation.

## Slice 3 — Docker Hub provider

9. Add strict pinned Docker Hub settings, public/PAT metadata, readiness, adapter, and registration.
10. Preserve upstream names beneath `dockerhub`, forwarding only provider-specific environment values.
11. Keep Docker Engine/local process capability separate.

## Slice 4 — Status, bootstrap, and UX

12. Wire both providers into explicit platform registration and capability discovery without direct-profile expansion.
13. Add actionable readiness/commissioning state for installation, binding, authentication, upstream connection, discovery, and live verification.
14. Add bounded bootstrap/commission scripts that activate only pinned identities beneath `C:\\Projects\\.kis-mcp` and preserve replaced state recoverably.
15. Reuse the supervised secrets launcher boundary; provider adapters do not unlock the vault.

## Slice 5 — Verification and authority reconciliation

16. Add focused red/green tests for contracts, stable names, generated TOML, read-only SQL policy, redaction, public/PAT Docker Hub state, mount containment, and effects.
17. Reconcile `SPEC.md`, provider product spec, operations, applicable platform concept/status material, KIS skill references, settings/contracts, and Control Center projections.
18. Run stale-roster/config/startup/commissioning sweeps, focused regression, scope/diff checks, canonical verification, and specialist review attempts.
19. Publish exact verified tree, create/inspect PR, merge only exact authorized head, delete review branch recoverably, synchronize local `main`, commission what is locally installable/authenticated, and close/clean the change.

## Recovery

Disable only the affected provider in runtime JSON, restore prior provider installation/runtime state from quarantine/recovery, and restart KIS. No policy weakening or permanent deletion is permitted.
