# Review Map Implementation Plan

**Goal:** Add deterministic source-bound Review Maps for exact KIS change evidence.

**Architecture:** Keep `inspect_change` as source authority. Build an additive pure Review Map projection from `InspectChangeResponse`, expose it through the same Discover change service, and advertise it as read-only navigation evidence.

**Tech Stack:** Python 3.13, FastMCP 4, pytest, Ruff, KIS change governance.

## Global constraints

- Stay inside `scope.json`.
- Reuse the exact existing change fingerprint; do not create a parallel identity.
- Do not introduce persistent Review Map state.
- Do not alter review, verification, merge-readiness, or mutation authority.

### Task 1: Contract and projection

- Add bounded Review Map limits and pure deterministic projection.
- Preserve diagnostics/unknowns and explicit incomplete/truncation semantics.
- Reject explicitly stale source fingerprints.

### Task 2: Discover exposure

- Add `build_review_map` to the existing change-tool registration path.
- Advertise `code.change.review-map` as read-only Discover capability.
- Preserve existing `inspect_change` defaults and contract.

### Task 3: Verification and closeout

- Add focused source-binding, deterministic ordering, bounds, truncation, registration, and capability tests.
- Run full Discover regression, Ruff, governed scope check, and `git diff --check`.
- Run independent public-contract review and resolve actionable findings before commit.
