# Work Management Registry Enrollment Implementation Plan

**Goal:** Close the remaining registry-to-Work-Management coverage defect without reopening merged change 125 or duplicating shared Project ownership.

**Architecture:** Treat the central KIS project registry as the enrolment source, overlay explicit Work Management mappings when present, inherit the sole backend when unambiguous, and preserve backend-coordinate conflict checks.

**Tech Stack:** Python 3.12, existing Work Management settings/contracts, pytest, JSON Schema.

## Constraints

- Stay inside `scope.json`.
- Do not modify `settings/projects.settings.json`; it is already authoritative.
- Do not touch `SPEC.md` or `docs/OPERATIONS.md` while change 136 owns them.
- Do not duplicate the shared GitHub Project coordinate.
- Preserve repository-neutral local projects.

## Execution

1. Preserve the post-merge residual implementation from change 125, then clean the merged 125 lifecycle.
2. Register this independent follow-up from current clean `main`.
3. Apply the bounded registry-bridge changes and focused regression tests.
4. Run the Work Management/Project Management/GitHub Projects affected suite and diff/scope checks.
5. Run required specialist reviews or record independent backend failure with manual exact-diff fallback.
6. Publish an exact review head, require canonical GitHub Actions, merge, refresh local `main`, restart/verify both runtimes, and clean the worktree.
