# Change Specification: HR-003 Remote Branch Retention

- **Change ID**: `218-hr003-remote-branch-retention`
- **Status**: Approved for implementation under operator-directed #419 execution
- **Development level**: Medium — bounded cross-component public contract/safety correction with focused tests and live exposure verification

## Outcome

Remove permanent remote branch deletion from ordinary KIS Work authority. Safe PR closeout must retain the remote review branch after merge while preserving exact-head merge and default-branch refresh guarantees.

## Authority and scope

- Authorities: `AGENTS.md`, `docs/TRUST-MODEL.md`, `policy/kis-mcp.policy.json`, issue #431 under parent #419.
- Owned paths: capability virtual surface, registered GitHub exact operation contract, closeout workflow, focused tests, trust-model wording, and this change record.
- Shared paths: none.
- Excluded: `SPEC.md` and coordinator paths owned by active Change 217; unrelated provider mutation semantics.
- Dependency: parent #419 is actively claimed; #412 is already closed.

## Requirements

- **REQ-001**: `pull-request-safe-closeout` MUST NOT call or require permanent remote branch deletion.
- **REQ-002**: the virtual `kis_github_delete_registered_branch` operation MUST no longer be discoverable or executable through capability control.
- **REQ-003**: the registered GitHub exact dispatcher MUST reject the removed delete operation as unknown rather than falling through to destructive behavior.
- **REQ-003A**: the internal `RegisteredGitHubOperations.delete_remote_branch` compatibility method MUST remain callable only as a deterministic no-side-effect HR-003 rejection; it is not a registered runtime operation.
- **REQ-004**: repository configuration MUST continue to keep GitHub `delete_branch_on_merge=false`.
- **REQ-005**: trust documentation MUST state that normal remote review-branch closeout retains the provider ref; a recovery SHA alone is not HR-003 quarantine.
- **REQ-006**: focused tests MUST prove the destructive virtual operation and schema are absent, closeout retains the branch, and unsupported delete dispatch fails closed.
- **REQ-007**: audit other currently exposed external delete operations and preserve findings under #431/#419 evidence; do not silently classify annotation/name hints as policy authority.

## Acceptance

1. **Given** the capability catalogue, **when** registered GitHub virtual operations are listed, **then** `kis_github_delete_registered_branch` is absent.
2. **Given** safe PR closeout, **when** the workflow is resolved, **then** merge is followed by default-branch refresh and local governed cleanup without remote branch deletion.
3. **Given** direct dispatch of the removed operation name, **when** arguments are validated, **then** execution fails with `UNKNOWN_REGISTERED_GITHUB_OPERATION` before mutation.
4. **Given** repository landing policy configuration, **when** applied, **then** `delete_branch_on_merge` remains false.
5. **Given** fresh runtime capability search after deployment, **when** destructive closeout is queried, **then** the registered remote-branch delete operation is not advertised.

## Risks and recovery

- Risk: removing a previously public virtual operation may break closeout callers that assumed remote deletion.
- Control: update the canonical workflow and focused contract tests in the same change; retention is safer and reversible.
- Recovery: revert the merge if needed; no remote ref is deleted by the new path.

## Out of scope

- Permanent disposal of retained/quarantined refs.
- Reinterpreting HR-003 beyond the existing trust-model semantics.
- Coordinator provenance changes owned by Change 217.
