# Closeout

Status: implementation and local verification complete; remote exact-head verification, merge, reconciliation, and cleanup pending.

## Delivered

- Added a provider-neutral persistent FastMCP client lifecycle with one outer connection per parent runtime and an injectable startup call.
- Reworked GitHub to use one shared runtime-scoped client and one `get_me` OAuth bootstrap instead of a per-downstream-session `StatefulProxyClient` process.
- Separated GitHub provider authentication configuration from repository and GitHub Project routing configuration.
- Added strict repository-local settings, local `origin` identity validation, linked-worktree Git metadata handling, and mutable selected-repository state.
- Wired normal Provider platform composition to construct and retain the selected-repository source and pass its live `current` callback into GitHub without reconnecting the authenticated provider client.
- Reconciled README, `SPEC.md`, `docs/OPERATIONS.md`, and `docs/PLATFORM-CONCEPT.md` with the implemented lifecycle and routing model.

## Review findings resolved

1. Added `tests/repositories/__init__.py` after the focused gate exposed a pytest module-name collision between repository and GitHub `test_settings.py` files.
2. Closed the architectural gap where mutable repository selection existed only as a test/injection seam: production Provider platform composition now owns the selector and retains it in `PlatformProviderRuntime`.
3. Extended the focused GitHub smoke gate to include platform-composition coverage and added an assertion that the script retains that test.
4. Reclassified the prior standalone GitHub OAuth and Project `#12` evidence as historical rather than current commissioning evidence.

Whole-diff review after these fixes found no remaining blocking correctness, scope, security, secret-handling, or documentation contradiction.

## Verification evidence

- `pwsh -NoProfile -File scripts/smoke-github-mcp.ps1`: passed; 93 focused tests passed. Live mode was not requested, so live authentication/mount/read/scope fields remain unclaimed.
- `git diff --check`: passed.
- `pwsh -NoProfile -File scripts/change-workflow.ps1 check`: passed for the full declared 057 path set.
- `pwsh -NoProfile -File scripts/verify.ps1`: passed on the current worktree.
  - Python files checked: 212.
  - Change-governance claims checked: 56.
  - FastMCP: 3.4.4.
  - pytest: 8.4.2.
  - Full pytest exit code: 0; two tests skipped.
  - Configuration, interpreter, dependency, syntax, line-ending, governance, and exact three-rule checks passed.

## Pull request and merge evidence

- Pull request: #72.
- Existing remote head before final local reconciliation: `cbf24b529e2bd1e9129643b5b1f7169d371b3656`.
- Exact final pushed head: pending the final verified metadata/code commit.
- Exact-head CI: pending.
- Merge commit: pending.

## Documentation impact

Authoritative documentation was reconciled in this change. Repository-local `gh_projects` configuration is documented as a routing boundary only and not as proof of GitHub Project existence or work-management commissioning. Fresh runtime-scoped OAuth evidence remains a separate supervised commissioning check.

## Recovery

Before merge, the change is reversible by closing PR #72 and retaining or removing the governed branch/worktree through normal Git operations. No OAuth token, credential, provider token store, or persisted secret is migrated by this slice. The implementation can be reverted by restoring the prior GitHub provider settings schema and provider construction.

## Cleanup evidence

Pending merge, post-merge claim reconciliation, and governed cleanup. Deferred change/worktree `040-context7-serena-adapters` remains excluded and must not be touched.
