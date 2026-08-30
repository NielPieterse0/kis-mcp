# Workflow Terminal Audit Implementation Plan

**Goal:** Make terminal workflow evidence canonical, typed, self-auditing, queryable, and efficiency-regression aware.

**Architecture:** Extend the existing PromotionController checkpoint/terminal receipt as the single machine authority. Add a bounded read-only audit projection over those receipts. Keep Work/GitHub provider filtering at the provider boundary so targeted reads are correct before truncation. Preserve implementation-review ownership and add no post-merge metadata commit requirement.

**Tech stack:** Python 3.13, FastMCP 4, pytest, GitHub MCP Project adapter, existing Work Management and once-through workflow modules.

## Tasks

1. Add failing regression coverage for durable telemetry, Done replay, generated closeout projection, typed identity rejection, audit registration, and targeted provider query forwarding.
2. Implement persisted stage/replay/provider metrics in the PromotionController and per-stage operation deltas in promotion invocation.
3. Extend `promotion-terminal-receipt-v1` with closeout projection and explicit source-to-provider-head verification lineage while retaining backwards-tolerant historical reads.
4. Add `workflow_terminal_audit(limit)` over recent terminal receipts with exact identities, delivery evidence, efficiency flags, and transition/provider-call budget reporting.
5. Strengthen promotion identity validation before provider activity.
6. Propagate board query through Work Management into the GitHub Project adapter before `item_limit`.
7. Update current product specification and governed change evidence.
8. Run focused/affected verification, governance checks, specialist review, exact-head Actions, merge, Work/source closeout, cleanup, restart proof, and terminal replay.

## Constraints

- Stay inside the declared schema-v4 scope.
- Canonical full repository verification runs once in GitHub Actions on the exact PR head.
- Tracked change files are historical after merge; terminal truth is not maintained by a second metadata-only commit.
- Promotion must not start a new substantive implementation review.