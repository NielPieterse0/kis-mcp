# Change 195 retained-payload reconciliation

Date: 2026-09-01
Parent programme: #491
Verifier: #503
Gap owner: #622 / Change 616

## Preserved source

The stale linked worktree `.work/worktrees/195-retirement-reconciliation` was found at base `5f5a319b389715ef9b5283e999ef33322ae5ff51` with 25 modified/untracked paths and 2,673 retained insertions. Before cleanup, its complete working-tree payload was committed unchanged to local archival ref `archive/change-195-retained-payload` at `1b5b767d50930d1984ba27a97bee9587b9416d06`.

The linked worktree was then removed while the archival ref was retained. No retained bytes were discarded to satisfy cleanup.

## Disposition of retained paths

- `scripts/prepublication-preflight.py`, `src/kis_mcp/repository_hygiene.py`, and `tests/repository_hygiene/**`: historical pre-publication experiment. Current authority remains `scripts/verify.py`, `scripts/change-governance.py`, `.gitattributes`, and canonical full pytest/Actions verification. The experiment is archived, not activated as a second verifier.
- `src/kis_mcp/workflows/completion/frozen_candidate.py`, `frozen_tools.py`, and their tests: historical frozen-candidate implementation. Current architecture replaces this with verified source handoff, `prepare_reviewable_pull_request`, durable PromotionReady checkpointing, and `converge_change_to_done`; the old FastMCP-3/MCP-2025 implementation is not an active dependency.
- Coordinator schemas/services and tests carrying `governance_handoff`, `decisions`, `assumptions_risks`, and `holds_deferred`: experimental Change 195 contract work was never authoritative on `main`. Its still-relevant typed-obligation intent is owned by the current Work/promotion architecture and follow-on workflow programme; the archived schema is not silently reintroduced into #491.
- Historical edits to `scripts/change-workflow.ps1`, `scripts/verify.py`, workflow platform descriptors, completion exports, and coordinator tests: superseded by later landed implementations on current `main`; no old file version is copied over newer authority.
- `.work/changes/195-retirement-reconciliation/**`: retained as historical programme evidence inside the archival ref only. It remains explicitly non-authoritative for current runtime behavior.

## Reconstruction obligations

The source issues inherited by #491 require retirement of obsolete reconstruction residue without losing still-valid obligations, not restoration of the abandoned local/VM verification architecture. Current `SPEC.md` keeps GitHub Actions as exact-head authority, current promotion uses durable exact-source evidence, and state cleanup remains recoverable/quarantine-bound.
## Retirement evidence

- Historical PR #323 was already closed.
- Historical PR #321 remained open until replacement proof was re-read: its Skills resource payload is reconstructed by Change 192 / PR #373, head `a7ef01764d04c9e8ff8c72be97477103f7260340`, merge `bb954d1a005e07d1a5afc899b291e8d177d6b702`. PR #321 was then closed with that evidence.
- Historical PR #326 remained open until replacement proof was re-read: repository-scoped Work projection is reconstructed by Change 190 / PR #371, head `9090479d31cedbb09c899ddaf6e718c26c89e5df`, merge `20fb433d78ddd4e85f0864e2c84f9535f11f2a3f`. PR #326 was then closed with that evidence.
- Historical PR #327 remained open until replacement proof was re-read: deterministic housekeeping is reconstructed by Change 194 / PR #377, merge `5f5a319b389715ef9b5283e999ef33322ae5ff51`, and operationalized by Change 199 / PR #381, merge `f9fec4d24bff7f6e3dffc431bdafb211ad6aed30`. PR #327 was then closed with that evidence.
- `C:\Projects\.kis-mcp\execution\local\runs` currently contains zero run directories, so the obsolete local-execution residue described by Change 195 is no longer active.

## Terminal disposition

The retained Change 195 tree is no longer an active worktree or runtime dependency. Its exact bytes remain reachable through `archive/change-195-retained-payload`; newer current authority remains on `main`. No obsolete Hyper-V, VirtualBox, local-runner, detached-verifier, or Change-186 serial reconstruction path is restored by this reconciliation.