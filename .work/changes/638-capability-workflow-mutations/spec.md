# Change Specification: Capability Workflow Mutations

- **Change ID**: `638-capability-workflow-mutations`
- **Status**: Active
- **Risk trigger**: `public_contract`

## Outcome
Restore executable governed-change operations used by progressive-disclosure workflows, including development and safe repository-worktree cleanup, without expanding the direct tool surface.

## Authority and scope
- Authority: `AGENTS.md`, current capability contracts/source/tests.
- Owned: `src/kis_mcp/capabilities/**`, `tests/capabilities/**`, this change record.
- Excluded: workflow descriptor definitions owned by active change #637; `kis-op` runtime operations.

## Requirements
- **REQ-001**: Capability discovery resolves governed development and cleanup operation names as eligible discoverable operations.
- **REQ-002**: `execute_read_action` dispatches `list_worktrees` and `validate_change_claims`; `execute_change_action` dispatches `create_change_worktree`, `commit_change`, and `cleanup_change_worktree` instead of returning `UNKNOWN_CAPABILITY_OPERATION`.
- **REQ-003**: Worktree creation, listing, validation, and cleanup delegate to the repository's governed `scripts/change-workflow.ps1` commands.
- **REQ-004**: Commit creation is restricted to a `change/*` branch and explicit repository-relative pathspecs.
- **REQ-005**: Progressive disclosure derives executable workflow steps from required steps that resolve to enabled operations or workflow IDs, so cleanup does not advertise unresolved executable work.

## Acceptance
1. Focused capability/execution tests pass.
2. Governed change scope check passes.
3. After landing/restart, live `kis-dev` discovery and dispatch no longer report unknown operation for these names.

## Risks and recovery
- Risk: new dispatcher contracts could bypass governance or broaden mutation authority.
- Mitigation: virtual discoverable operations only; existing policy boundary and governed scripts remain authoritative.
- Recovery: revert the bounded commit; no durable external state is required by the change itself.

## Out of scope
Workflow descriptor source changes owned by active Change 637 and any cleanup behavior beyond the existing governed repository cleanup command.
