# Implementation Plan: Discover Git Evidence Resilience

## Goal

Fix the live `GIT_METADATA_TOO_LARGE` false-negative with the smallest behavior-preserving safety correction.

## Architecture

Keep `GitReader` and all fixed Git command templates unchanged. In `git_metadata.py`, continue bounded reading for `.git` pointer/config/HEAD/alternate text records, but validate the opaque Git index by canonical path and regular-file identity rather than reading its bytes into Discover. This matches the actual trust boundary: Discover never parses the index directly; Git consumes it through the already isolated fixed command surface.

## Tasks

### T1 — RED regression for realistic large index

- Add a test that creates enough tracked files for `.git/index` to exceed `git_metadata_max_bytes`.
- Prove the current implementation returns `GIT_METADATA_TOO_LARGE`.
- Extend the same regression to a linked worktree.

Verify: focused test fails for the expected reason before production code changes.

### T2 — Minimal metadata validation correction

- Add one helper that validates an optional regular metadata file without reading its content.
- Use it only for the Git index.
- Preserve canonical containment, existing-component link/reparse rejection, regular-file validation, and all bounded readers for text metadata.

Verify: T1 passes; existing invalid/oversized pointer metadata tests still pass.

### T3 — Review and verification

- Run the complete `tests/discover/test_git_reader.py` file.
- Run relevant Discover Git/change tests if affected by the helper.
- Run change-governance scope check.
- Run canonical repository verification.
- Review the diff against REQ-001..REQ-005 and record residual risk.

## Recovery

One bounded revert restores prior behavior. No settings/schema/state migration is required.
