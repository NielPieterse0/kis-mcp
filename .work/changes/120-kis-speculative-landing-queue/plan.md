# KIS Speculative Landing Queue Implementation Plan

**Goal:** Deliver and commission the smallest complete KIS-owned speculative integration queue for registered GitHub repositories.

**Architecture:** Keep queue ordering/generation/state logic provider-neutral in `github_merge_queue.py`; keep Git/GitHub effects behind a registered backend that reuses `RegisteredGitHubOperations`; expose five discoverable virtual operations; integrate normal and Work Management workflows; reuse canonical verification for candidate ref pushes.

**Runtime:** Python 3.13, FastMCP, local Git object operations, authenticated GitHub CLI only through the registered exact-GitHub boundary, GitHub Actions canonical verification, JSON repository configuration, generated state under `C:\Projects\.kis-mcp`.

## Constraints

- Stay inside `scope.json` and the three hard rules.
- GitHub/Git and repository documents remain authoritative; queue state is generated/rebuildable.
- Add/execute tests before claiming behavior.
- Do not duplicate exact ref publication, authentication, or repository registration logic.
- Queue landing must fail closed on stale base/head/evidence.

## Tasks

1. Register SPEC-120 in Work Management and create the governed worktree.
2. Add failing tests for exact enqueue identity, cumulative candidates, generation invalidation, ALLGREEN landing, and exact Actions evidence.
3. Implement strict v1 JSON settings and atomic generated queue state.
4. Implement provider-neutral coordinator and registered GitHub backend.
5. Expose bounded status/enqueue/reconcile/dequeue/land operations and workflow descriptors.
6. Trigger canonical verification on queue candidate branch pushes.
7. Add focused production-adapter tests and commissioning smoke entrypoint.
8. Reconcile authoritative docs and lifecycle evidence.
9. Run scope check, focused tests, canonical repository verification, diff checks, and code review.
10. Publish exact reviewed commit, create PR, verify exact PR-head Actions, merge, refresh tracking, and clean the governed worktree.
11. Restart/reload commissioned runtime and exercise a live queue candidate through exact Actions and base advancement; record evidence in SPEC-120/closeout.