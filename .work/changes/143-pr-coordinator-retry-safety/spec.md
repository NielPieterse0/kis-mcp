# Change Specification: PR Coordinator Retry Safety

- **Change ID**: `143-pr-coordinator-retry-safety`
- **Status**: Implemented; pending exact-head integration
- **Risk Profile**: rigorous

## Outcome

Make exact registered PR preparation retry-safe across publication and PR-creation partial success without weakening SHA/base/branch gates.

## Authority and scope

- Authoritative sources: issue #211, `AGENTS.md`, registered GitHub project/repository bindings, exact Git/GitHub state.
- Owned paths: registered GitHub exact operations, completion coordinator/tool, focused workflow tests, this change record.
- Shared paths: none.
- Excluded paths: merge queue, Work Management command semantics, unrestricted GitHub/GraphQL administration.
- Dependencies: bounded `gh` registered-repository operations and `execute_change_workflow` verification.
- Integration owner: change 143.

## Requirements

- **REQ-001**: Repeating the same approved exact request after publication or PR response loss converges without duplicate external state.
- **REQ-002**: Recovery accepts only exact branch tree/parent/source identity and exact PR head/base/title/body identity.
- **REQ-003**: Closed/merged or conflicting PR history prevents duplicate PR creation.
- **REQ-004**: Partial failures expose typed stage, completed steps, and conservative retryability.
- **REQ-005**: Existing SHA/base/branch approval gates remain fail-closed.

## Acceptance

1. Response-loss, stale-state, repeated-invocation, terminal-PR, and conflict tests pass.
2. Public completion tool truthfully advertises idempotence and serializes partial-success diagnostics.
3. Exact-head CI and merge gates pass before issue completion.
