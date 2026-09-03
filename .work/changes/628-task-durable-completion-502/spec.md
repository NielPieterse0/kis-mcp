# Change Specification: Task Durable Completion 502

- **Change ID**: `628-task-durable-completion-502`
- **Status**: Active
- **Risk Profile**: standard — `external_action`, `persistent_state`, `public_contract`

## Outcome

Make `prepare_reviewable_pull_request` use MCP 2026 Tasks as the normal durable transport boundary so dropped/502 responses do not obscure completion state or encourage duplicate registered GitHub mutations.

## Authority and scope

- `AGENTS.md`, current `SPEC.md`, issue/Work `#663` / `WORK-663`, FastMCP 4 task contracts, existing completion coordinator contracts/tests.
- Owned implementation: `src/kis_mcp/mcp2026.py`, `src/kis_mcp/workflows/completion/**`, focused tests, `SPEC.md`, and this change record.
- MCP task state remains transport state; KIS operation identity, receipts, Work state, and registered GitHub reconciliation remain durable authority.

## Requirements

- **REQ-001**: Normal `prepare_reviewable_pull_request` execution MUST require MCP Tasks rather than silently execute synchronously.
- **REQ-002**: A non-Tasks client MUST have an explicit synchronous compatibility surface rather than an implicit fallback on the normal operation.
- **REQ-003**: Task creation MUST expose a retrievable task handle before transport loss can make completion state ambiguous, and reconnect polling MUST resolve the same terminal result.
- **REQ-004**: Reconnect/retrieval MUST NOT re-execute the completion service or duplicate registered GitHub mutations.
- **REQ-005**: Existing exact source/default/head identity, retry classification, completion operation identity, and reconciliation semantics MUST remain unchanged.

## Acceptance

1. Primary completion tool registers task mode `required`; compatibility tool registers task mode `forbidden`.
2. Completion-specific task test disconnects after task creation, reconnects with `tasks/get`, receives terminal reviewable result, and proves one service execution.
3. Existing response-loss reconciliation regressions remain green.
4. Focused tests, change-scope check, review, and exact-head GitHub Actions pass before merge.
