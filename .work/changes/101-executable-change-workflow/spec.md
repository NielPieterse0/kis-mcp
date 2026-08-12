# Change Specification: Executable Change Workflow

- **Change ID**: `101-executable-change-workflow`
- **Status**: Approved by operator continuation request
- **Risk Profile**: standard

## Outcome

Execute bounded change-aware verification selections and specialist reviews through existing KIS tool contracts without arbitrary command or policy authority.

## Authority and scope

- Authorities: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, `policy/kis-mcp.policy.json`, and `docs/OPERATIONS.md`.
- Reuse `select_change_verification`, `run_verification`, and `review_change_with_agent`; do not duplicate their selection, execution, or reviewer backends.
- Owned paths are exactly those in `scope.json`; `policy/**` is excluded.
- No new provider, scanner, reviewer backend, command surface, or hard-rule authority.

## Requirements

- **REQ-001**: Expose one bounded executable change workflow that selects current verification handoffs before executing any check.
- **REQ-002**: Execute only verification IDs returned by the current selector, through the existing `run_verification` tool contract.
- **REQ-003**: Run only allowlisted existing specialist review purposes through `review_change_with_agent`, with a bounded review count.
- **REQ-004**: Aggregate selection evidence, each verification result, each review result/error, and an overall execution status without inventing review-pass semantics.
- **REQ-005**: Preserve nested middleware and original tool validation for every invoked step.
- **REQ-006**: Expose no arbitrary command, executable, nested tool name, policy override, approval bypass, mutation, or permanent-delete parameter.
- **REQ-007**: Keep structural/orchestration failures distinct from HR-001/HR-002/HR-003 policy outcomes.

## Acceptance

1. The workflow invokes selection first and executes only selected verification IDs.
2. Verification failures and incomplete executions are retained in the aggregate result rather than hidden.
3. Requested reviews are restricted to the seven existing specialist purposes and use the current backend/model validation unchanged.
4. The workflow surface contains no `command`, executable, arbitrary operation, or policy parameter.
5. Existing selector, runner, reviewer, gateway registration, scope checks, focused tests, and canonical verification pass.

## Risks and recovery

- Risk: orchestration could become a second execution authority. Mitigation: fixed internal step names and nested calls through original FastMCP contracts with middleware enabled.
- Risk: reviewer findings could be misrepresented as a pass/fail gate. Mitigation: record review completion separately; overall `passed` means execution completed and selected verification passed, not that reviews found nothing.
- Risk: one backend can fail independently. Mitigation: record bounded review errors accurately without claiming a review result.
- Recovery: revert the slice; the existing selector, verification runner, and reviewer remain independently usable.

## Out of scope

- Govern gateway/catalogue implementation.
- Historical repository/test-gap intelligence and performance investigation.
- Commissioning, PR-closeout, or top-level task-to-PR coordination.
- New reviewer backends, arbitrary commands, policy changes, or new hard rules.
