# Change Specification: Registered Default Branch Refresh

- **Change ID**: `118-registered-default-branch-refresh`
- **Status**: Approved for implementation
- **Risk Profile**: standard

## Outcome
Refresh a registered repository's local default-branch tracking ref to exact GitHub truth as part of KIS landing, without changing the local working branch.

## Authority and scope
- GitHub MCP observation supplied as `expected_remote_default` is remote truth.
- KIS registered-project settings are repository/local-root authority.
- Only the verified registered repository's `refs/remotes/origin/<default>` may be changed.
- `github_exact.py`, generic fetch/sync behavior, and local working-branch mutation are out of scope.

## Requirements
- **REQ-001**: Expose `kis_github_refresh_registered_default_branch` as an approval-gated discoverable operation with external + local-change effects.
- **REQ-002**: Require a full expected GitHub default-branch SHA and verify it against the registered remote before mutation.
- **REQ-003**: Verify local `origin` resolves to the registered GitHub repository; reject mismatch before network mutation.
- **REQ-004**: Materialize the exact remote commit only when absent, re-observe remote state, then atomically CAS-update only the tracking ref.
- **REQ-005**: Never update `refs/heads/<default>` or the working tree; report local, tracking, GitHub SHAs and `same_commit | tree_equivalent | content_divergent`.
- **REQ-006**: Make refresh a required registered-repository lifecycle step immediately after exact PR merge and before remote review-branch deletion, and immediately before creation of a new governed worktree.

## Acceptance
1. Stale `origin/main` is refreshed to the exact GitHub `main` SHA while tree-equivalent local `main` remains unchanged.
2. Remote drift, registered-origin mismatch, or compare-and-swap conflict fails closed.
3. Capability discovery and safe PR closeout expose the bounded operation without expanding the direct tool surface.
4. Focused verification, repository verification, review, PR landing, and post-merge commissioning pass.

## Recovery and operator hold
The previous tracking SHA is returned so the tracking ref can be restored without deleting content. Keep Work Management `SPEC-118` / issue #159 open and non-final after technical closeout for operator review.
