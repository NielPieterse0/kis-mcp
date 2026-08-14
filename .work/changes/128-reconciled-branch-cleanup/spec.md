# Change Specification: Reconciled Branch Cleanup

- **Change ID**: `128-reconciled-branch-cleanup`
- **Status**: Ready for review
- **Complexity**: medium
- **Risk triggers**: destructive

## Outcome

Make canonical cleanup safely normalize locally divergent but verifiably landed reconciled branches before non-forced worktree cleanup.

## Authority and scope

- Authoritative sources: `AGENTS.md`, repository change-governance contracts, and local Git history.
- Owned paths: `scripts/change-workflow.ps1`, `scripts/git-workflow.py`, `tests/test_git_workflow.py`, and this change record.
- Shared paths: none.
- Excluded paths: `scripts/change-governance.py` and its tests remain owned by concurrent change 125.
- Dependencies: none; the implementation deliberately avoids 125-owned files.
- Integration owner: none.

## Requirements

- **REQ-001**: Cleanup must continue to accept normal ancestry as the primary landed proof.
- **REQ-002**: A non-ancestor branch may be prepared for cleanup only when local Git proves its exact tree is reachable from the base history or every unique patch is equivalent on the base.
- **REQ-003**: Before normalizing a reconciled branch, preserve the original head at `refs/kis-recovery/cleanup/<change-id>` and reject conflicting recovery refs.
- **REQ-004**: Normalize with `git reset --keep` to an exact verified base SHA, then delegate removal to the existing non-forced governance cleanup.
- **REQ-005**: Dirty, divergent, unregistered, or otherwise ineligible worktrees remain fail-closed.

## Acceptance

1. **Given** a clean reconciled branch whose exact tree is reachable from `main`, **When** cleanup preview runs, **Then** it reports the branch as landed with explicit evidence instead of `CHANGE_BRANCH_UNMERGED`.
2. **Given** that reconciled branch, **When** cleanup preparation runs, **Then** its original head is preserved, the local branch is normalized to the verified base with `--keep`, and canonical cleanup can remove it non-forced.
3. **Given** an unlanded divergent branch, **When** cleanup preparation runs, **Then** it fails without moving the branch or creating a recovery ref.
4. Existing cleanup-preview behavior and affected tests remain green.

## Risks and recovery

- Risk: cleanup preparation moves a local branch pointer immediately before deletion.
- Recovery: the original head is retained under a deterministic recovery ref before any normalization; dirty or ambiguous states are rejected.

## Out of scope

- Changing `scripts/change-governance.py` while change 125 owns it.
- Altering GitHub merge or reconciliation behavior.
