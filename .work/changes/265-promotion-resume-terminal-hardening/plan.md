# Promotion Resume Terminal Hardening Implementation Plan

**Goal:** Make PromotionReady-to-Done reuse persisted external identities, reconcile uncertain mutations, avoid half-applied Work/source closeout, and persist one terminal delivery receipt.

**Architecture:** Reuse the controller's persisted blocked-stage observation as the sub-stage checkpoint. Promotion stages consume that observation before rediscovery or mutation. Add typed preflight identity checks in `PromotionStageService`, reconcile uncertain merge results from provider truth, make source closure resumable after Work completion, and synthesize a durable terminal receipt once cleanup completes.

**Tech stack:** Python 3.13, FastMCP 4 runtime operations, existing Work/GitHub provider contracts, pytest, PowerShell post-land regression harness.

## Constraints

- Stay inside `scope.json`.
- Preserve substantive implementation review ownership before PromotionReady.
- Preserve exact-head Actions, Work merge readiness, exact-head merge, landed truth, documentation completion, and safe cleanup gates.
- Do not add a second canonical local full-verification pass.
- Treat transport uncertainty by authoritative reread before another mutation.

## Tasks

1. Add failing tests for persisted Actions-run reuse and no workflow-history rescan.
2. Add failing tests for merge-response uncertainty reconciliation.
3. Add failing tests for Work-complete/source-close interruption and resume.
4. Add failing tests for typed Work/change identity preflight.
5. Add failing tests for one durable terminal receipt and Done no-op replay.
6. Implement the smallest promotion/controller changes satisfying those tests.
7. Run focused once-through and post-land tests, change-governance check, specialist review, and final pre-publication verification.
8. Publish exact head, require exact-head CI and Work readiness, merge, reconcile Work/docs/source closure, and cleanup.
