# 020 Discover Change Inventory Specification

## Status

Approved bounded implementation slice. Development level: Medium.

## Outcome

Add the first D2 Discover change-intelligence foundation: a deterministic, bounded, read-only local Git inventory for staged, unstaged, untracked, renamed, copied, deleted, type-changed, and conflicted paths.

## Architecture

`GitReader` remains the only Discover subprocess boundary. A new immutable `change_contracts.py` module defines the provider-neutral response records. `GitReader.inspect_local_changes()` uses fixed Git argument templates and the existing isolated, bounded execution path, merges staged/unstaged/untracked observations by current path, and returns stable sorted records. A checked-in JSON Schema snapshots the internal response contract.

## Requirements

1. Accept one project path already governed by `ReadAuthority`.
2. Validate Git metadata and repository containment before running change commands.
3. Use fixed local Git commands only; no caller-supplied refs, arguments, environment, URLs, or executable paths.
4. Read staged changes with `git diff --no-ext-diff --no-textconv --cached --name-status -z --find-renames --find-copies`.
5. Read unstaged changes with `git diff --no-ext-diff --no-textconv --name-status -z --find-renames --find-copies`.
6. Read untracked paths with `git ls-files --others --exclude-standard -z`, while neutralizing external attributes and excludes-file configuration.
7. Normalize Git status codes to `added`, `copied`, `deleted`, `modified`, `renamed`, `type_changed`, `unmerged`, or `unknown`.
8. Preserve the current path and optional previous path for rename/copy records.
9. Merge multiple observations for the same current path into one record with independent staged, worktree, and untracked state.
10. Sort records deterministically by case-folded path, exact path, and previous path.
11. Bound retained records by configured `max_files` and surface truncation diagnostics.
12. Discard incomplete trailing NUL records when bounded Git output truncates a command.
13. Return structural availability diagnostics rather than HR policy decisions.
14. Do not register a public `inspect_change` tool in this slice.

## Response contract

The internal response contains:

- `schema_version` fixed at `1`;
- `source` fixed at `local_git`;
- canonical project and repository paths;
- zero or more deterministic change records;
- summary counts for total, staged, unstaged, untracked, renamed, copied, deleted, and conflicted paths;
- diagnostics;
- `truncated`.

Each change record contains:

- `path`;
- optional `previous_path`;
- optional `staged_status`;
- optional `worktree_status`;
- `untracked`.

## Acceptance criteria

- Focused tests prove clean repositories, staged/unstaged/untracked merging, rename and copy parsing, delete/type/conflict normalization, deterministic ordering, configured record limits, bounded-output truncation, non-repository handling, and schema validation.
- Existing Discover Git tests remain green.
- Architecture tests still confine subprocess use to `git_reader.py`.
- Change-scope and whitespace checks pass.
- The full locked repository verification passes on the reconciled final branch head.

## Exclusions

Public tool registration, request contracts, ref/commit/range inspection, diff content, symbol impact, dependency impact, verification handoffs, remote PR evidence, settings changes, Work policy, providers, Skills, startup, and documentation authority updates are outside this slice.

## Recovery

The change is additive except for the bounded method added to `GitReader`. Reverting the branch commit removes the method, contract module, schema, tests, and change artifacts without persistent data migration or generated-state cleanup.
