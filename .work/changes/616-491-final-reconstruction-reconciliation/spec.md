# Change Specification: 491 Final Reconstruction Reconciliation

- **Change ID**: `616-491-final-reconstruction-reconciliation`
- **Status**: Active
- **Risk Profile**: medium / persistent-state

## Outcome

Repair the missing Change 190 landed record and terminally reconcile retained Change 195 reconstruction residue without restoring obsolete execution architecture or losing retained bytes.

## Authority and scope

- Authoritative sources: #491, #503, #622, #365, #367, Git/GitHub landed facts, current `SPEC.md`.
- Owned paths: repaired Change 190 `change.md`, dated Change 195 reconciliation audit, and this Change 616 record.
- Retained dirty Change 195 bytes are preserved on `archive/change-195-retained-payload` before worktree removal.
- Historical PR closure is allowed only after exact landed replacement evidence is proven.

## Requirements

- **REQ-001**: Reconstruct Change 190 evidence from PR #371 without inventing historical facts.
- **REQ-002**: Preserve and disposition the complete Change 195 dirty payload before removing its stale worktree.
- **REQ-003**: Verify/close historical harvest PRs only when exact replacement payload has landed.
- **REQ-004**: Do not reactivate obsolete local/VM verification or reconstruction authority.

## Acceptance

1. Change 190 record contains exact reviewed head and merge identity.
2. Change 195 payload is recoverable from an archive ref and no stale linked worktree remains.
3. PR #321/#326/#327 closure is replacement-evidence-backed; #323 was already closed.
4. Current main remains the sole implementation authority and repository verification remains Actions-based.

## Risks and recovery

- Risk: deleting useful historical residue. Recovery: archive exact bytes before cleanup; retain archive ref.
- Risk: stale evidence presented as current authority. Recovery: label the archive historical and use current main/GitHub facts only.