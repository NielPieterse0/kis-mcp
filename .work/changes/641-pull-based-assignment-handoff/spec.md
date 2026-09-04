# Change Specification: Pull Based Assignment Handoff

- **Change ID**: `641-pull-based-assignment-handoff`
- **Status**: Active
- **Complexity**: Large
- **Risk triggers**: `persistent_state`, `public_contract`

## Outcome

Complete issue #544 by making pull-based resume return the same deterministic persisted Work handoff already returned by successful claim/take-next activation, while preserving Work ownership as the authority and avoiding a second coordinator/public mutation surface.

## Authority and scope

- Authoritative sources: `AGENTS.md`, `SPEC.md`, `docs/COORDINATOR-MODULE-PRODUCT-SPEC.md`, GitHub issue #544 and its inherited #426 requirements, current Work Management contracts.
- Owned paths: exact paths in `scope.json`.
- Excluded paths: active #619 Project adapter paths and `SPEC.md` while separately owned.
- Dependency evidence: #491, #542, and #543 are landed/closed before implementation.

## Requirements

- **REQ-001**: `project_management_current_work` MUST re-read authoritative Active Work state for the requested execution owner before returning an assignment.
- **REQ-002**: A uniquely selected Active item MUST receive the same activation materializer used by claim/take-next so resume returns the persisted deterministic `task_handoff` rather than reconstructing it from chat context.
- **REQ-003**: Missing, different, or ambiguous ownership MUST NOT materialize a handoff.
- **REQ-004**: Resume MUST remain read-only with respect to Work claim/lifecycle state.
- **REQ-005**: Production registration MUST forward the activation materializer to the resume surface.
- **REQ-006**: The public boundary MUST remain pull-based; external conversation/project references do not establish mutation authority.
- **REQ-007**: Existing claim/take-next behavior and active #619 paths MUST remain unchanged.

## Acceptance

1. **Given** one Active Work item owned by the pulling execution owner, **when** `project_management_current_work` runs, **then** it returns the selected item plus the persisted `task_handoff` and calls the materializer with exact project/repository/issue identity.
2. **Given** Active work owned by another execution owner, **when** resume is requested, **then** no assignment is selected and no handoff materialization occurs.
3. **Given** the normal platform registration path, **when** the Work tools are mounted with an activation materializer, **then** that same materializer is wired into resume.
4. Existing Work Management tool regression coverage remains passing.
5. Governed scope validation and change checks pass.

## Risks and recovery

- Risk: resume could recreate or mutate claim state. Mitigation: it only reads inventory/selects current owner and materializes immutable handoff state.
- Risk: stale owner could receive a packet. Mitigation: selection is performed from a fresh Project inventory before materialization and mismatched/ambiguous owners return no assignment.
- Risk: overlap with #619. Mitigation: its owned Project adapter/tool paths remain explicitly excluded.
- Recovery: revert this bounded change; existing claim/take-next behavior remains intact.

## Out of scope

- Creating a new public coordinator mutation tool.
- Modifying #619-owned Project adapter paths or `SPEC.md` while separately claimed.
- Push-launching or addressing ChatGPT Web conversations.
- Replacing Work Management admission, selection, claim, or coordinator generation/run/lease/fence authority.
