# Closeout: Promotion Efficiency

## Implemented scope

- PR creation reuses Work title/context and no longer rereads the source issue.
- Registered commit reconciliation owns review-branch observation; promotion no longer pre-reads the branch.
- Exact-head Actions discovery removes the duplicate PR read, performs one workflow-scoped list page, and persists one run ID for direct retry polling.
- Landed inclusion skips history traversal entirely: exact SHA equality is the fast path and local `git merge-base --is-ancestor` proves inclusion when the default branch has advanced.
- Empty documentation reconciliation completes in one logical call while applying due then complete states internally.
- Existing PromotionReady reuse in PR preparation remains authoritative and avoids duplicate implementation verification/review.

## Efficiency evidence

- Baseline normal path: approximately 17 provider/command-boundary calls before unchanged cleanup/restart handling.
- New normal path: approximately 13 calls.
- Reduction: 4/17 = 23.5%.
- Removed happy-path calls: source issue read, review-branch pre-read, PR read before Actions, second no-op documentation reconciliation call.
- Actions discovery bound: up to ten list pages → one workflow-scoped page; bound-run retry → one direct run read.
- Landed history fallback: up to ten 100-commit provider pages → zero provider history pages; exact equality or local ancestry proof is conclusive.

## Validation evidence

- Focused checks: 74 affected tests passed across once-through promotion, project-management documentation, and traceability coverage.
- Governance: `pwsh -File scripts/change-workflow.ps1 check` passed on the current tree; `git diff --check` and Python compilation passed.
- Repository verification: reserved for provider-native GitHub Actions on the exact PR head.
- Specialist review: final code-quality and architecture reviews are clean. Safety/security provider routes failed their output contract; required exact-diff fallback found no material security blocker after checking registered reconciliation, exact-head Actions/merge guards, source confinement, and documentation lifecycle ordering.
