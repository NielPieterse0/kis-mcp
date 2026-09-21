# Change Specification: Historical Change Recovery Maze

- **Change ID**: `718-historical-change-recovery-maze`
- **Status**: Active
- **Complexity**: Medium
- **Risk triggers**: public_contract

## Outcome

Make historical merged-change recovery and follow-up transfer deterministic so stale landed claims do not block safe follow-up work or force manual branch/worktree surgery.

## Authority and scope

- Authoritative sources:
- Owned paths:
- Shared paths:
- Excluded paths:
- Dependencies:
- Integration owner:

## Requirements

- **REQ-001**: A live linked worktree's own scope record overrides the stale copy of the same change record already present on the base branch.
- **REQ-002**: A schema-v3+ claim already recorded on its base releases path ownership when no live worktree exists, even if the preserved historical branch later advanced.
- **REQ-003**: Fully landed live branches continue to project closed; unmerged residual work in a live worktree remains active and protected.
- **REQ-004**: Recovery must not require deleting preserved branches, rewriting history, or weakening overlap checks.

## Acceptance

1. A landed historical scope plus a live branch with residual commits resolves to the live active claim.
2. Removing that clean worktree releases the landed historical claim without deleting the branch.
3. A fresh governed follow-up may then claim the same path.
4. Existing malformed-history compatibility and active-change protections continue to pass.

## Risks and recovery

- Risk: releasing ownership too early could permit overlapping active work.
- Recovery: live linked worktrees remain authoritative; only landed base records without a live worktree are released.

## Out of scope

- Changing once-through workflow stages, PR approval policy, or GitHub branch-retention policy.
