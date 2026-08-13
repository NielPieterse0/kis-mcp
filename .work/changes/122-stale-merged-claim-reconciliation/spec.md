# Change Specification: Stale Merged Claim Reconciliation

- **Change ID**: `122-stale-merged-claim-reconciliation`
- **Status**: Approved prerequisite cleanup
- **Complexity**: small
- **Risk triggers**: none

## Outcome

Make repository governance reflect GitHub truth by closing only stale local lifecycle claims for changes 115-119, whose implementation PRs are already merged.

## Requirements

- Change only the five historical `scope.json` status values plus this 122 record.
- Verify PRs 155, 158, 163, 162, and 166 are merged before closing their claims.
- Do not close or mutate source issues, Project operator holds, production code, policy, or documentation.
- Preserve historical work-management metadata and all evidence fields.
- Canonical change-governance verification must report no stale exclusive-path conflicts afterward.

## Bootstrap exception

The normal governed `new` command cannot create 122 because stale change 119 claims its own `scope.json`; a manual isolated worktree is therefore required to repair the blocking lifecycle state.

## Recovery

Revert the 122 commit to restore the prior lifecycle markers. No production behavior or external data is changed.
