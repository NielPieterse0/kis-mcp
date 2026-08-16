# Change Specification: Inspect Change Native Git Semantics

- **Change ID**: `160-inspect-change-native-git-semantics`
- **Status**: Approved
- **Complexity**: Medium
- **Risk Triggers**: `public_contract`
- **Source Issue**: #273

## Outcome

Fix #273 by making linked-worktree working-tree inspection match native Git line-ending semantics while preserving bounded non-executing change evidence.

## Authority and scope

- Authorities: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, `policy/kis-mcp.policy.json`, `docs/OPERATIONS.md`, and issue #273.
- Owned implementation: `src/kis_mcp/discover/git_reader.py`.
- Owned tests: `tests/discover/test_local_change_inventory.py`, `tests/discover/test_change_targets.py`, `tests/discover/test_git_hardening.py`.
- Change lifecycle record: `.work/changes/160-inspect-change-native-git-semantics/**`.
- No shared paths or implementation dependencies.

## Proven root cause

On Windows, native Git may obtain line-ending behavior from system/global configuration. The current Discover Git subprocess environment suppresses both system and global Git configuration. A linked worktree created under effective `core.autocrlf=true` can therefore be clean to native Git while KIS re-evaluates every CRLF tracked file under different conversion semantics and reports it modified.

A disposable 200-file linked-worktree reproducer produced native `git diff` count `0` and current `inspect_change(source="working_tree")` count `200`. The same HEAD, index, worktree metadata, and files were used. This disproves stale/shared Discover state as the cause of #273 and keeps the fix local rather than depending on #278.

## Requirements

- **REQ-001**: Working-tree change inspection must preserve the effective native Git line-ending configuration that materially determines index/worktree comparison, while retaining KIS suppression of repository-selection overrides, prompts, pagers, credentials, external diff execution, global attributes, and other existing non-executing controls.
- **REQ-002**: The effective configuration probe must be read-only, bounded by the existing Git deadline/output limit, and validate accepted line-ending values before replaying them into isolated evidence commands.
- **REQ-003**: Linked-worktree inspection must agree with native Git for a clean CRLF checkout whose clean state depends on system/global `core.autocrlf` semantics.
- **REQ-004**: Regression coverage must exercise linked-worktree tracked, staged, unstaged, and untracked inventory and preserve repository `.gitattributes` behavior.
- **REQ-005**: Existing source-fingerprint race detection and fixed non-executing Git command controls must remain intact.

## Acceptance

1. **Given** a linked worktree whose effective native Git configuration resolves `core.autocrlf=true`, **when** native Git reports no tracked modifications, **then** `GitChangeReader`/`inspect_change` reports no false tracked modifications and produces a valid source fingerprint.
2. **Given** staged, unstaged, and untracked changes in that linked worktree, **when** KIS inspects the working tree, **then** its path/status inventory matches native Git evidence for the same HEAD/index/worktree.
3. **Given** repository `.gitattributes` line-ending declarations, **when** KIS gathers change evidence, **then** those repository attributes remain active while global attributes remain suppressed as before.
4. Focused Discover tests, change-scope validation, Ruff for changed Python files, and `git diff --check` pass on the final branch.

## Risks and recovery

- Risk: broadly re-enabling user/system Git configuration could reintroduce executable or non-deterministic Git behavior.
- Control: copy only validated line-ending semantics into the already isolated Git invocation instead of re-enabling arbitrary configuration.
- Risk: probing effective configuration could race with configuration changes during inspection.
- Control: resolve and validate the effective line-ending semantics on bounded diff/status reads; the existing repeated inventory/guard comparisons reject any material source-evidence change during inspection.
- Recovery: revert change 160; no persistent data, provider state, schema, or migration is introduced.

## Out of scope

- #265, #274, #261, #270, #241, or other active lanes.
- General Git configuration passthrough, executable filters, user/global attributes, hooks, credentials, network access, or provider changes.
- #278 state ownership/namespace implementation; #273 reproduction shows stale/shared state is not causal.
