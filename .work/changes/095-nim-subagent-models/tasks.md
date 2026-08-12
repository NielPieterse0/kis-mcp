# Tasks: NIM Sub-agent Models

- [x] Confirm authority, parallel worktrees, and non-overlapping scope.
- [x] Implement separate experimental benchmark allowlist and client path.
- [x] Implement fixed review-quality and latency suitability evaluation.
- [x] Keep production `nano`, `super`, and `ultra` profiles unchanged.
- [x] Verify benchmark is discoverable external + read-only and not direct.
- [x] Run focused tests: 30 passed.
- [x] Run `pwsh -File scripts/change-workflow.ps1 check`.
- [x] Run canonical `pwsh -File scripts/verify.ps1` to completion before merge.
- [x] Review and commit benchmark seam.
- [x] Publish and merge benchmark PR #105.
- [x] Live-smoke all allowlisted models through the commissioned external benchmark surface.
- [x] Reconcile repeated candidate evidence: no experimental candidate is robust enough for automatic production promotion from 095.
- [x] Complete final local cleanup: `kis-op` runs from current `main`, the 095 worktree is removed, and the merged local 095 branch is absent.
- [x] Prepare the final reconciled closeout metadata for exact publication to remote `main`.
