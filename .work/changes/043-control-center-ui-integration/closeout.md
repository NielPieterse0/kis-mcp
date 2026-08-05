# Control Center UI Integration Closeout

- **Status**: In progress
- **Change ID**: `043-control-center-ui-integration`
- **Development level**: Complex
- **Review**: Pending

## Requested outcome

Integrate the KIS Control Center MCP App into the primary provider runtime and expand it into a truthful read-only operational dashboard while preserving Desktop Commander unchanged.

## Governance history

The primary worktree was clean and synchronized on `main`. The normal `scripts/change-workflow.ps1 new` path was attempted first. The command bridge returned an internal tool failure before exposing repository output when the required repeated path claims were supplied. Under the emergency exception documented in `AGENTS.md`, the native worktree tool created `.work/worktrees/043-control-center-ui-integration` on `change/043-control-center-ui-integration`; all five governance artifacts were then registered before production code edits. Repository validation remains mandatory before implementation.

## Implemented scope

Pending.

## Verification evidence

Pending.

## Review findings

Pending.

## Recovery

Pending final diff. The intended recovery is to revert the feature commits and remove the `control-center` provider entry. The slice must not introduce migrations, credential changes, Desktop Commander changes, or permanent state transitions.

## Residual risks

Pending final review.
