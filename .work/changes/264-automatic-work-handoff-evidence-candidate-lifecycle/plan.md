# Automatic Work Handoff Evidence Candidate Lifecycle Implementation Plan

**Goal:** Make #586's once-through handoff/evidence/candidate primitives automatic, durable, and idempotent at successful Work activation.

**Architecture:** Keep `TaskHandoffStore` as the single durable state owner. Inject a Work-activation coordinator into Project Management tools, materialize contracts only after a proven Active claim, persist candidate ownership/source-path receipts and immutable evidence lineage, and let promotion consume persisted candidate/change identity while extending evidence by provider/post-merge references.

**Tech stack:** Python 3.13 via repository `uv` lock, FastMCP 4, Windows atomic file replacement/locking, pytest, existing KIS GitHub/Work workflows.

## Constraints

- Stay within `scope.json`.
- Preserve the existing evidence validity classes and three Work hard rules.
- Do not kill any process unless exact Work/contract/source/PID/instance ownership is proven.
- Do not create a handoff for preview or failed activation.
- Preserve idempotent retry/re-entry across activation, candidate reuse, evidence append, and promotion.

## Tasks

1. Add automatic Work activation materialization and atomic contract/port allocation.
2. Add durable immutable evidence lineage and candidate ownership receipts.
3. Add candidate reuse, live-proof persistence, and exact-owner-only shutdown.
4. Derive PromotionReady from accumulated lineage and preserve immutable Work-origin identity.
5. Extend provider exact-head, merge, and post-merge receipts into the same evidence lineage.
6. Add parallel/retry/failed-activation/evidence/exact-cleanup regression coverage.
7. Reconcile `SPEC.md`, run focused/governance/canonical verification, obtain specialist review, then publish/merge/cleanup through governed closeout.
