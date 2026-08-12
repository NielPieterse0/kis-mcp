# Change Specification: Verification Selection Policy

- **Change ID**: `099-verification-selection-policy`
- **Status**: Approved by operator continuation request
- **Risk Profile**: standard

## Outcome

Add deterministic change-aware verification selection between Discover handoffs and Work execution without executing checks or adding policy authority.

## Authority and scope

- Authorities: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, `policy/kis-mcp.policy.json`, `docs/OPERATIONS.md`, and the slice boundary recorded by change 093.
- Reuse existing Discover `analyze_change` impact handoffs, project verification declarations, and Work `run_verification` contracts.
- Owned paths are exactly those in `scope.json`; active 098 paths are excluded by non-overlap.
- No dependency or policy change.

## Requirements

- **REQ-001**: Reconcile change-impact verification handoffs against the current project verification declarations before selection.
- **REQ-002**: Select only profiles already executable by Work; report missing, stale, and unsupported handoffs explicitly.
- **REQ-003**: Produce stable priority ordering and a caller-bounded maximum of 1–50 selections.
- **REQ-004**: Keep selected items non-executable evidence (`execution_available=false`); selection performs no process or external action.
- **REQ-005**: Expose a read-only `select_change_verification` tool with no command or free-form execution arguments.
- **REQ-006**: Preserve existing `run_verification` behavior and HR-001/HR-002/HR-003 unchanged.

## Acceptance

1. Applicable current handoffs are selected in deterministic repository/test/lint/typecheck priority order.
2. Missing declarations, stale handoffs, and unsupported profiles are returned as bounded selection issues, never executed.
3. Selection truncation reports omitted count and never silently widens the caller limit.
4. The public selection tool is read-only and accepts no command text.
5. Existing verification workflow, gateway registration, scope, and canonical repository verification pass.

## Risks and recovery

- Risk: stale Discover evidence could point to a changed command. Mitigation: exact profile/category/source/argument reconciliation against current project declarations.
- Risk: selection could be mistaken for authorization. Mitigation: fixed non-executable result contract and no process runner in this service.
- Recovery: revert the slice; existing single-ID verification execution remains intact.

## Out of scope

- Executing the selected checks (Slice 5).
- Specialist review orchestration (Slice 5 after parallel 098 lands).
- Commissioning/PR closeout automation (Slice 6).
- Top-level delivery coordination (Slice 7).
- Changes to `SPEC.md`, `docs/OPERATIONS.md`, or active 098-owned review paths.
