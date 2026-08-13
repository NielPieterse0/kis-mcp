# Registered Default Branch Refresh Implementation Plan

**Goal:** Make exact remote-tracking refresh a bounded KIS landing primitive and required post-merge closeout step.

**Architecture:** Add a small `github_tracking` module that composes the existing registered-GitHub exact-operation class, validates `origin`, verifies an expected GitHub SHA against the registered remote, materializes only that exact commit if needed, and compare-and-swap updates the tracking ref. Register it as a virtual capability and insert it immediately after PR merge in the closeout descriptor.

**Tech stack:** Python, Git plumbing, FastMCP capability catalogue, pytest, existing KIS registered-project registry.

## Constraints
- Stay inside the 118 scope and avoid active 116/117 owned paths.
- Tests precede behavior changes.
- No generic fetch/sync command and no local working-branch rewrite.
- Remote truth enters as an exact full SHA observed through GitHub MCP.

### Task 1 — Contract and red tests
- Add project-operation tests for approval, origin scoping, exact remote verification, fetch-on-missing-object, CAS update, relation reporting, and no local branch mutation.
- Add capability/workflow tests for discoverability, effects, dispatch, and post-merge ordering.
- Run focused tests and record expected failures.

### Task 2 — Minimal implementation
- Add `github_tracking.py` with schema, validator, operation class, and dispatcher.
- Wire the virtual operation into capability surface/execution.
- Insert refresh immediately after registered merge in `pull-request-safe-closeout`.
- Add focused development documentation.

### Task 3 — Verification and landing
- Run focused tests, scope check, full verifier, and independent review; fix findings and rerun affected checks.
- Commit, reconcile/publish exact tree, open PR, verify checks/head, merge exact approved head, refresh tracking ref, clean branch/worktree, and verify local/GitHub state.
- Keep Work Management `SPEC-118` open and non-final for operator review.
