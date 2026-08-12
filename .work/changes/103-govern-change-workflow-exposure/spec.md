# Change Specification: Govern Change Workflow Exposure

- **Change ID**: `103-govern-change-workflow-exposure`
- **Status**: Approved by operator continuation request
- **Risk Profile**: lean

## Outcome

Expose the bounded executable change workflow through Govern capability recommendation without adding execution authority.

## Authority and scope

- Authorities: `AGENTS.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, and existing capability/workflow contracts.
- Owned production path: `src/kis_mcp/workflows/platform.py`; focused descriptor test and this lifecycle record only.
- `policy/**` is excluded; no configuration or operation schema changes.

## Requirements

- **REQ-001**: Add one discoverable workflow descriptor for the existing `execute_change_workflow` operation.
- **REQ-002**: Declare `execute_change_workflow` as the only executable step and use its existing runtime capability `operation.execute_change_workflow`.
- **REQ-003**: Describe verification selection/execution and specialist review aggregation without implying new authorization or review-pass semantics.
- **REQ-004**: Preserve existing direct-profile limits and all current workflow descriptors unchanged.

## Acceptance

1. `workflow_descriptors()` contains the new workflow with exactly one executable step: `execute_change_workflow`.
2. Its effect is process/local supervised execution, not external authority.
3. Existing descriptor tests remain green and no policy/configuration file changes.

## Risks and recovery

- Risk: catalogue metadata could imply broader authority than the tool owns. Mitigation: capability and executable step point only to the existing bounded operation.
- Recovery: revert this metadata-only slice; Slice 5 remains directly callable/discoverable as an operation.

## Out of scope

- New orchestration behavior, policy rules, provider access, verification profiles, reviewer backends, or top-level delivery coordination.
