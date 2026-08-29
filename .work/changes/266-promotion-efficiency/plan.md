# Promotion Efficiency Implementation Plan

**Goal:** Remove duplicate provider observation and no-op ceremony while preserving Change 265 terminal correctness.

**Architecture:** Keep the durable PromotionController stage/checkpoint model. Optimize inside stages by assigning each fact one authority owner, persisting its identity, and replacing repeated rediscovery with direct validation or bounded fallback.

**Tech Stack:** Python 3.13, FastMCP 4, pytest, registered GitHub exact operations, Work Management.

## Global constraints

- Stay inside `scope.json`.
- Preserve P0 crash/retry checkpoints and exact identity guards.
- Use focused/affected local verification only; canonical full verification belongs to exact-head GitHub Actions.
- Do not start another KIS implementation review during promotion.

### Task 1: Eliminate duplicate provider reads

- [x] Reuse Work title/context for PR creation.
- [x] Let registered reconciliation own review-branch observation.
- [x] Remove redundant PR read before Actions discovery.
- [x] Scope initial Actions discovery to one workflow page and retain direct persisted-run polling.

### Task 2: Bound post-merge reconciliation

- [x] Bound landed-history fallback to one page and prefer exact SHA equality.
- [x] Collapse empty documentation reconciliation into one external call while retaining due→complete lifecycle internally.

### Task 3: Prove efficiency and correctness

- [x] Add regression tests for no issue read, one-page Actions discovery, and one-call no-op documentation completion.
- [x] Preserve existing tests for persisted Actions polling and Work/source-close retry recovery.
- [ ] Run all affected once-through, project-management documentation, and traceability tests.
- [ ] Run change governance, whitespace, and targeted compilation checks.
- [ ] Record exact before/after call-budget evidence and specialist review findings.

### Task 4: Governed delivery

- [ ] Commit and publish the exact reviewed source.
- [ ] Create the exact PR without duplicate local canonical verification.
- [ ] Require exact-head provider-native GitHub Actions and Work merge readiness.
- [ ] Merge the exact approved head, reconcile documentation/Work/source closure, verify restart receipt, and clean the governed worktree.
