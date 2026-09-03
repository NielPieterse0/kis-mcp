# Change Specification: Capability Workflow Mutations

- **Change ID**: `638-capability-workflow-mutations`
- **Status**: Active
- **Risk trigger**: `public_contract`

## Outcome
Restore executable `create_change_worktree` and `commit_change` operations for the governed development workflow without expanding the direct tool surface.

## Authority and scope
- Authority: `AGENTS.md`, current capability contracts/source/tests.
- Owned: `src/kis_mcp/capabilities/**`, `tests/capabilities/**`, this change record.
- Excluded: workflow descriptor definitions owned by active change #637; `kis-op` runtime operations.

## Requirements
- **REQ-001**: Capability discovery resolves both missing operation names as eligible discoverable operations.
- **REQ-002**: `execute_change_action` dispatches both operations instead of returning `UNKNOWN_CAPABILITY_OPERATION`.
- **REQ-003**: Worktree creation uses the repository's governed `scripts/change-workflow.ps1 new` path.
- **REQ-004**: Commit creation is restricted to a `change/*` branch and explicit repository-relative pathspecs.

## Acceptance
1. Focused capability/execution tests pass.
2. Governed change scope check passes.
3. After landing/restart, live `kis-dev` discovery and dispatch no longer report unknown operation for these names.

## Risks and recovery
- Risk: new dispatcher contracts could bypass governance or broaden mutation authority.
- Mitigation: virtual discoverable operations only; existing policy boundary and governed scripts remain authoritative.
- Recovery: revert the bounded commit; no durable external state is required by the change itself.

## Out of scope
`list_worktrees`, `cleanup_change_worktree`, and broader workflow-catalog reconciliation follow after the development path is operational.
