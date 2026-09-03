# Linked Worktree Metadata Bounds Implementation Plan

**Goal:** Accept legitimate repository-scale active config and packed-refs metadata in linked worktrees without weakening control-pointer/path/link safety.

**Architecture:** Keep two byte budgets in Discover Git metadata validation: the existing small control-metadata budget for pointer-like/control records, and the existing bounded Git-output budget for repository-scale collections. Preserve all existing canonical-path, boundary, identity, symlink/reparse, include-depth, and bounded-read checks.

**Tech stack:** Python Discover implementation and pytest regression coverage; governed KIS change workflow for verification, review, publication, merge, and cleanup.

## Global constraints

- Stay inside `scope.json`.
- Do not alter repository policy or the configured byte limits themselves.
- Keep `.git`, `commondir`, `HEAD`, loose refs, and alternates on `git_metadata_max_bytes`.
- Use `git_max_output_bytes` only for active config collections and `packed-refs`.

## Execution

1. Add regressions for linked worktrees with config and packed-refs larger than 4 KiB but below the collection budget.
2. Split metadata validation inputs into control and collection byte limits.
3. Route config and packed-refs through the collection limit while retaining control records on the control limit.
4. Run focused Discover tests and governed scope/repository verification.
5. Obtain required code-quality and safety-security independent reviews.
6. Publish, merge after exact-head CI, verify the corrected runtime against commodity #289, then perform only governed merged-and-clean worktree cleanup.