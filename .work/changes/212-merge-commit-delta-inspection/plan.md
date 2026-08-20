# Merge Commit Delta Inspection Implementation Plan

**Goal:** Fix #407 with one deterministic merge-commit rule in the shared Discover target reader.

**Architecture:** Resolve immutable commit identity first, inspect its parent cardinality, then build one bounded name-status delta. Ordinary commits retain existing `diff-tree` behavior; exactly two parents use `git diff <first-parent> <merge>`; more than two parents fail closed before evidence is reported. Existing inspect/analyze/verification/review consumers continue to consume the same shared inventory.

**Tech stack:** Python, Git CLI through hardened `GitReader`, pytest, KIS change/review/verification workflows.

## Constraints

- Stay inside `scope.json`; update scope before any additional consumer test path.
- Tests precede behavior changes.
- No reviewer architecture or Serena changes.
- No unrelated cleanup.

## Tasks

1. Add failing regression tests for two-parent merge payload, ordinary commit preservation, and multi-parent fail-closed behavior.
2. Implement parent-cardinality resolution and deterministic first-parent merge delta selection.
3. Add minimal consumer regression proving shared corrected inventory reaches downstream evidence.
4. Run focused pytest, governance `check`, and required `code-quality` plus `api-contracts` reviews.
5. Commit, publish, create PR, require exact-head GitHub Actions success, merge, reconcile Work Management, and clean the governed worktree.
