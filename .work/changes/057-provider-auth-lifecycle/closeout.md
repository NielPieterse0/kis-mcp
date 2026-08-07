# Closeout

Status: complete. Implementation, local verification, exact-head Windows verification, documentation reconciliation, and PR merge are complete. Governed worktree/branch cleanup follows immediately after this closeout metadata is merged.

## Delivered

- Added a provider-neutral persistent FastMCP client lifecycle with one outer connection per parent runtime and an injectable startup call.
- Reworked GitHub to use one shared runtime-scoped client and one `get_me` OAuth bootstrap instead of a per-downstream-session `StatefulProxyClient` process.
- Separated GitHub provider authentication configuration from repository and GitHub Project routing configuration.
- Added strict repository-local settings, local `origin` identity validation, linked-worktree Git metadata handling, and mutable selected-repository state.
- Wired normal Provider platform composition to construct and retain the selected-repository source and pass its live `current` callback into GitHub without reconnecting the authenticated provider client.
- Reconciled README, `SPEC.md`, `docs/OPERATIONS.md`, and `docs/PLATFORM-CONCEPT.md` with the implemented lifecycle and routing model.
- Repaired the reusable Windows verification workflow so its online dependency sync primes the canonical offline uv cache and its full canonical verifier executes from a self-contained `C:\Projects` fixture with the approved shared Skills root.

## Review findings resolved

1. Added `tests/repositories/__init__.py` after the focused gate exposed a pytest module-name collision between repository and GitHub `test_settings.py` files.
2. Closed the architectural gap where mutable repository selection existed only as a test/injection seam: production Provider platform composition now owns the selector and retains it in `PlatformProviderRuntime`.
3. Extended the focused GitHub smoke gate to include platform-composition coverage and added an assertion that the script retains that test.
4. Reclassified the prior standalone GitHub OAuth and Project `#12` evidence as historical rather than current commissioning evidence.
5. Deferred repository-boundary validation until repository routing is actually used so an optional disabled GitHub provider cannot break gateway startup in another checkout location.
6. Corrected Windows CI environment parity without weakening runtime rules: the workflow now primes `C:\Projects\.kis-mcp\uv-cache`, stages a self-contained canonical checkout under `C:\Projects\kis-mcp`, and mirrors checked-in Skills to `C:\Projects\.agents\skills` before canonical verification.

Whole-diff review after these fixes found no remaining blocking correctness, scope, security, secret-handling, or documentation contradiction.

## Verification evidence

- `pwsh -NoProfile -File scripts/smoke-github-mcp.ps1`: passed; 93 focused tests passed. Live mode was not requested, so live authentication/mount/read/scope fields remain unclaimed.
- `git diff --check`: passed.
- `pwsh -NoProfile -File scripts/change-workflow.ps1 check`: passed for the full declared 057 path set.
- `pwsh -NoProfile -File scripts/verify.ps1`: passed on the final implementation tree.
  - Python files checked: 212.
  - Change-governance claims checked: 56.
  - FastMCP: 3.4.4.
  - pytest: 8.4.2.
  - Full pytest exit code: 0; two tests skipped.
  - Configuration, interpreter, dependency, syntax, line-ending, governance, and exact three-rule checks passed.
- Windows Actions run `31158901336`: passed on exact implementation head `4fc3e1a3dcfbfd2df015e1e1e5d196e5553239f8`.
  - locked dependency synchronization passed;
  - work-management settings and governance validation passed;
  - 183 focused P5 tests passed;
  - canonical verification fixture preparation passed;
  - full canonical repository verification passed;
  - all post-job steps passed.

## Pull request and merge evidence

- Pull request: #72 — `Fix runtime-scoped provider authentication lifecycle`.
- Exact verified PR head: `4fc3e1a3dcfbfd2df015e1e1e5d196e5553239f8`.
- Exact-head Windows Actions run: `31158901336`, conclusion `success`.
- Merge commit: `633a33c16acd8b37f9729840c282bc23a93a909e`.
- Merged to `main` on 2026-08-07.

## Documentation impact

Authoritative documentation was reconciled in this change. Repository-local `gh_projects` configuration is documented as a routing boundary only and not as proof of GitHub Project existence or work-management commissioning. Fresh runtime-scoped OAuth evidence remains a separate supervised commissioning check.

## Commissioning boundary

Live runtime-scoped GitHub OAuth was not re-commissioned by automated CI and is not claimed by this closeout. The implemented lifecycle is verified structurally and behaviorally; an actual browser OAuth sign-in remains a separate supervised operational commissioning check.

## Recovery

The implementation is now merged. Recovery is by an ordinary Git revert of merge commit `633a33c16acd8b37f9729840c282bc23a93a909e` or a later corrective change. No OAuth token, credential, provider token store, or persisted secret was migrated by this slice.

## Cleanup evidence

The change claim is closed by this reconciliation. After this metadata-only closeout commit merges, run the governed cleanup command for `057-provider-auth-lifecycle` from clean primary `main`. Deferred change/worktree `040-context7-serena-adapters` remains excluded and must not be touched. The final operator report records the cleanup result.
