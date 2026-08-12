# Specialist Review Purposes Implementation Plan

**Development level:** Medium — expands an external advisory contract but does not alter repository mutation or policy authority.

**Architecture:** keep one `CodeReviewAgent` and one `review_change_with_agent` operation. Centralize purpose text in one fixed mapping and validate against its key set. Reuse the existing evidence collector, NVIDIA/Codex adapters, normalization, budgets, and fallback rules.

## Tasks

1. Replace two-purpose branching with a fixed purpose registry containing the five approved specialist rubrics plus the existing two.
2. Keep the shared immutable review execution path unchanged.
3. Add regression coverage for every specialist purpose and no-mutation instructions.
4. Reconcile `SPEC.md` and `docs/OPERATIONS.md` current behavior.
5. Run scope/whitespace checks, full repository verification, review, exact-head PR delivery, and governed cleanup.

## Constraints

- No new reviewer backend or model profile.
- No nested delegation or mutation authority.
- No invented performance measurements.
- No overlap with active change 096.
