# Context7 and Serena adapter status

## Disposition

Change `040-context7-serena-adapters` is closed in governance and held unmerged. Its branch and worktree are preserved until the whole-server modularity update defines the final composition seam.

The local package installations are complete and independent of Git integration:

| Tool | Version | Installed location | Readiness | Executed |
| --- | --- | --- | --- | --- |
| Context7 MCP | `3.2.5` | `C:\Projects\.kis-mcp\context7` | `ready` | No |
| Serena | `1.6.1` | `C:\Projects\.kis-mcp\serena` | `ready` | No |

## Module boundary

- Context7 implementation: `src/kis_mcp/tools/context7/`
- Serena implementation: `src/kis_mcp/tools/serena/`
- Shared Tools composition: `src/kis_mcp/tools/platform.py`
- Pinned settings: `settings/tools/context7.tool.json` and `settings/tools/serena.tool.json`
- Pinned contracts: `contracts/tools/context7/` and `contracts/tools/serena/`
- Installation workflows: `scripts/install-context7.ps1` and `scripts/install-serena.ps1`

`server.py` imports only the Tools composition entry point. It does not import Context7 or Serena adapter internals. This branch must still be reconciled with the planned whole-server modularity refactor before integration.

## Installation controls

Context7 was acquired into an isolated dependency tree with npm package scripts disabled. The complete acquisition directory was scanned clean before promotion.

Serena was acquired as a complete wheelhouse. The wheelhouse was scanned clean, an offline Python 3.11 candidate was built, and the complete candidate tree was scanned with Microsoft Defender before promotion. The Serena provider was not executed during acquisition, installation, scanning, or readiness verification.

## Enforcement status

- HR1-07 resolves only invocation-controlled Serena mutation destinations.
- HR2-06 delegates unchanged Serena shell command semantics to the corrected shared command resolver.
- HR3-07 resolves an exact memory artifact into the existing quarantine path; restoration and post-quarantine provider metadata consistency remain deferred.
- Provider-managed Serena state roots are readiness invariants beneath `C:\Projects`, not broad per-invocation blockers.
- Context7 uses the approved external-provider boundary and has no HR hard-block entry.

## Verification at hold point

- Focused tests: 71 passed.
- Full repository verification: passed.
- Context7 installed descriptor: `ready`.
- Serena installed descriptor: `ready`.
- Change-governance and scope checks: passed before the claim was closed.

## Deferred work

1. Complete the whole-server modularity assessment and refactor.
2. Reconcile `compose_tool_runtime(...)` with the final server composition contract.
3. Execute live MCP smoke and upstream contract checks for both providers.
4. Complete HR3 restoration and Serena metadata-consistency testing.
5. Review the final rebased branch, raise a PR, merge only if safe, and clean up only after integration.

## Resume location

```text
Branch:   change/040-context7-serena-adapters
Worktree: C:\Projects\kis-mcp\.work\worktrees\040-context7-serena-adapters
```

Do not delete the branch, worktree, acquisition evidence, or installation backups while the change is held.
