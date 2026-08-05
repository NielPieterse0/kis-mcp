# Git Workflow Tooling Implementation Plan

**Goal:** Add deterministic local Git workflow commands for specialized diffs, PR readiness, cleanup previews, and recoverable merged-worktree cleanup.

**Architecture:** Implement a standalone Python CLI under `scripts/` that uses only fixed `git` subprocess calls and the existing change-governance module. Keep remote forge mutations outside this CLI. Harden the existing cleanup path narrowly so ordinary behavior remains unchanged and Windows long-path failures become recoverable moves instead of incomplete deletion.

## Tasks

### Task 1: Red tests for structured diff and readiness
- Add temporary-repository fixtures and failing tests for `diff-summary`, including modified, added, deleted, renamed, copied, binary, commit, numstat, path-filter, and bounded-output behavior.
- Add failing tests for `pr-readiness` covering clean ready, dirty, detached, branch-not-ahead, missing governance claim, and scope violation cases.

### Task 2: Red tests for cleanup preview and recovery
- Add failing tests for `cleanup-preview` classification of clean merged, dirty, unmerged, unregistered, and long-path-risk worktrees.
- Add governance regression tests for ordinary cleanup, partial Git removal with unregistered filesystem remnant, and failure with registration retained.

### Task 3: Implement the fixed-shape Git workflow CLI
- Add strict repository, ref, and path validators.
- Add bounded Git execution and parsers for name-status, numstat, commits, ahead/behind, branch, and worktree evidence.
- Implement `diff-summary`, `pr-readiness`, and `cleanup-preview` JSON contracts.
- Add deterministic error envelopes and exit codes.

### Task 4: Harden governed cleanup
- Add `core.longpaths=true` to worktree removal.
- Detect post-failure registration state.
- Move only clean, merged, unregistered remnants intact to a timestamped `C:\Projects\.backup` location.
- Delete the local branch only after the worktree is unregistered and safely removed or moved.
- Preserve ordinary cleanup behavior and worktree pruning.

### Task 5: Wrapper and documentation
- Add `scripts/git-workflow.ps1` using the repository-managed Python environment with a bounded fallback.
- Document command inputs, outputs, examples, boundaries, recovery behavior, and the separation from GitHub connector mutations.

### Task 6: Review, verification, and integration
- Run focused tests, governance scope checks, whitespace validation, and the full repository verifier.
- Review security, argument validation, bounds, compatibility, recovery, and concurrent-worktree safety.
- Reconcile change artifacts, commit, push, create/review/merge the PR, verify `main`, and clean only change `045`.
