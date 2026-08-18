# Change Specification: Post Actions Reconstruction

- **Change ID**: `186-post-actions-reconstruction`
- **Status**: Active umbrella programme
- **Complexity**: large

## Outcome

Reconstruct the intended post-Actions KIS state from the restored pre-outage baseline. First classify all post-boundary work, retire obsolete Actions-loss workaround architecture and machine residue, then selectively reimplement only still-valid value as fresh serial governed slices.

## Authority and baseline

- Restored authority commit: `ef2b337264577d4a3d347dae38f4ae4579c531ba`.
- Restored authority tree: `443a77461e5dabdb53cdf0a904c135ea0b8d8baa`.
- Historical recovery boundary: `1365d84de30360b880f95bc5c51101ddeab9006c` / same tree.
- Change 185 preservation evidence and post-boundary inventory are historical evidence, not implementation authority.
- Current `AGENTS.md`, applicable product/contracts/tests, and current GitHub evidence govern each child slice.

## Programme invariants

- Every implementation slice is a fresh governed child change from then-current merged `main`.
- Each child must verify, review, merge, align/reconcile, and clean before the next child begins unless an explicit dependency-free documentation-only preparation is proven safe.
- Never mechanically cherry-pick or re-merge an old post-boundary PR.
- Preserve old PRs/commits as evidence and harvest only intentionally selected behavior/tests/contracts.
- FastMCP 3.x work uses normative MCP `2025-11-25`; FastMCP 4.x / MCP `2026-07-28` remains separate future migration work.

## Verification workflow optimization invariant

Before reconstruction implementation starts, audit and optimize the governed verification/review/closeout sequence itself. Prefer an evidence-efficient lifecycle where implementation and all evidence-bearing metadata are finalized first, producing one immutable final head; run the required reviews and canonical repository verification against that same exact head; then merge and perform non-code administrative reconciliation/cleanup without creating a new commit that invalidates evidence.

Do not preserve historical sequencing merely because it was previously used. Remove redundant verification passes where repository authority permits it, but never weaken exact-head, required-review, merge-readiness, or closeout guarantees. Any workflow improvement must be encoded in canonical repository tooling/documentation/tests before later slices rely on it.

## Required slice structure

1. **Slice 1 — Recovery classification and workflow optimization.** Build the complete evidence-linked post-boundary register; classify every merged/open/frozen change and Project item; audit #329/#336/#339 and dependent workaround work; identify machine-installed residue; determine the lean reconstruction dependency order; and implement any safe verification-lifecycle optimization needed before repetitive merges begin.
2. **Slice 2 — Execution-workaround retirement and host cleanup.** Retire obsolete Hyper-V/VirtualBox/local-runner direction and dependent records; remove only confirmed-unused host software/state/artifacts through recoverable/safe procedures; retain explicitly approved independently useful primitives only through fresh code changes.
3. **Subsequent slices — Selective reconstruction.** Reimplement approved independent fixes/features in dependency order from current `main`, using preserved history as evidence rather than merge authority.
4. **Final architecture slices.** Re-author the MCP/platform programme against the reconstructed codebase rather than restoring stale #181 assumptions.

## Acceptance

- One authoritative recovery register accounts for all post-boundary work and Project records.
- #329, #336, #339 and their dependent workaround-only work have explicit retain/harvest/retire decisions and host-cleanup evidence.
- No obsolete Actions-loss architecture remains active accidentally.
- Every retained feature is reintroduced only through a fresh bounded change from current `main`.
- The repetitive verification/review lifecycle is measurably leaner in execution count without reducing exact-head assurance.
- Programme completion leaves local `main`, GitHub `main`, runtime source, Work Management and applicable documentation reconciled.

## Out of scope

- Blind replay/cherry-pick of post-boundary PRs.
- FastMCP 4.x migration.
- Restoring local Windows/VM execution merely because historical implementations exist.
