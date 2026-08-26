# Change Specification: FastMCP 4 / MCP 2026

- **Change ID**: `239-fastmcp4-mcp2026`
- **Status**: Approved for implementation by Work #475 and operator instruction
- **Complexity**: Large
- **Risk triggers**: architecture_boundary, persistent_state, public_contract

## Outcome

Upgrade kis-mcp to FastMCP 4 and align the KIS MCP boundary with the applicable MCP 2026-07-28 contracts, especially Tasks, stateless request metadata, progress/cancellation, and modern wire/schema behavior, without interrupting kis-op.

## Authority and scope

- Repository authority: `AGENTS.md`, applicable `SPEC.md`, `docs/OPERATIONS.md`, machine contracts/tests.
- Work authority: GitHub/Work #475.
- MCP authority: local corpus rooted at `C:\Projects\References\mcp-specification\mcp-docs-2026-07-28-direct-md-clean\markdown\000-index.md`; schema authority is `055-specification-schema-reference.md`.
- Owned paths: `pyproject.toml`, `uv.lock`, `src/kis_mcp/**`, `tests/**`, `SPEC.md`, `docs/OPERATIONS.md`, `docs/operations/**`, this change record.
- Supabase remains parked and invisible; kis-op is excluded operationally.

## Requirements

- **REQ-001 FastMCP 4**: pin the selected FastMCP 4 release and required direct dependencies; migrate removed/moved SDK interfaces.
- **REQ-002 Stateless-first**: durable KIS authority must not depend on MCP session/connection objects. Protocol version and client capability facts are request scoped. Delivery telemetry may consume request metadata only for correlation.
- **REQ-003 Tasks**: install `io.modelcontextprotocol/tasks` and task-enable selected multi-minute KIS operations. Task-capable clients may receive `CreateTaskResult`; clients without the extension retain synchronous execution.
- **REQ-004 Durable authority**: MCP task state must not become a second KIS work authority. Existing Work/execution/receipt/fencing state remains authoritative; MCP task IDs are transport-facing execution handles/correlation.
- **REQ-005 Reconnect**: a task handle remains queryable after the creating client disconnects and a fresh client reconnects to the same running KIS service.
- **REQ-006 Time domains**: foreground request timeout, KIS execution deadline, stall detection, and MCP task TTL are distinct concepts and must not be represented by one giant timeout.
- **REQ-007 Progress**: task/foreground progress uses stable request/task correlation and bounded human-readable messages where FastMCP supports it; progress cannot suppress the maximum execution deadline.
- **REQ-008 Cancellation**: task cancellation is cooperative. Where KIS owns an underlying process handle, cancellation attempts to terminate that process and must not claim durable KIS cancellation solely because the MCP request was received.
- **REQ-009 Wire/schema**: use SDK-v2 snake_case Python surfaces; preserve MCP wire aliases/result discriminators; validate JSON Schema 2020-12 behavior and modern content acceptance including ResourceLink.
- **REQ-010 Legacy cleanup**: remove stale FastMCP 3 camelCase runtime/test access unless a specific legacy compatibility boundary requires it and is documented.
- **REQ-011 Provider recovery**: validate provider/proxy disconnect/reconnect behavior on FastMCP 4.
- **REQ-012 Supabase**: preserve parked implementation while exposing no Supabase tools/providers/capabilities/status to normal tool users.
- **REQ-013 Deferred 2026 work**: every valuable 2026 improvement discovered but not implemented must have a separate Work issue with an objective activation trigger before closeout.
- **REQ-014 Operations**: canonical documentation describes FastMCP 4 / MCP 2026 behavior, task durability boundaries, recovery expectations, and commissioning evidence without duplicating volatile change history.

## Selected task candidates

Task-enable operations whose normal execution can legitimately exceed a foreground request budget: full verification, agent/code review, post-merge commissioning, and reviewable-PR completion/orchestration where the runtime registration can safely carry `TaskConfig`. Keep bounded discovery/status/read operations synchronous.

## Acceptance evidence

1. Exact pinned FastMCP 4 environment imports and focused migration tests pass.
2. Modern boundary evidence records `server/discover`, request-scoped metadata, tools/list, and tools/call without relying on initialize/session state.
3. A task-enabled long operation returns a task handle to a task-capable client and remains retrievable by task ID from a fresh client connection after disconnect.
4. The same operation remains callable synchronously when Tasks are not negotiated/available.
5. Progress is observable on the task path and the underlying execution deadline remains bounded independently.
6. Cancelling a task with an owned child process invokes cooperative process termination; the test distinguishes cancellation intent from durable KIS work-state authority.
7. Tool schemas are valid modern JSON Schema expectations and SDK-v2 snake_case access is used in KIS runtime code; result wire aliases remain correct.
8. ResourceLink/modern content is accepted by the gateway/result path.
9. Provider/proxy recovery is exercised under FastMCP 4.
10. Supabase is absent from user-visible tools, capabilities, and status surfaces.
11. `scripts/change-workflow.ps1 check`, focused tests, canonical `scripts/verify.ps1`, required reviews, exact-head CI, and live kis-dev commissioning pass.
12. Work #475 is completed only after merge evidence and governed cleanup.

## Risks and recovery

- FastMCP 4 is prerelease API surface: exact pin + lock + contract tests contain drift.
- Task state in the current deployment uses FastMCP/Docket in-process storage; KIS durable Work/execution receipts remain authoritative. Server-process restart persistence requires a durable Docket backend and is not falsely claimed by this change unless deployed and commissioned.
- Cancellation races with process completion: best-effort process termination is attempted only when a live owned PID is known; terminal evidence wins over cancellation intent.
- Rollback is the normal governed revert to the prior exact dependency/code tree; no irreversible state migration is introduced.

## Out of scope

- Supabase activation or setup.
- Redesigning KIS around MCP task storage.
- Adding unrelated MCP 2026 features solely because FastMCP exposes them.
- Interrupting or restarting kis-op.
- Introducing Redis/Valkey infrastructure without a separately approved deployment requirement.
