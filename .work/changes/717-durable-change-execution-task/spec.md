# Change Specification: Durable Change Execution Task

- **Change ID**: `717-durable-change-execution-task`
- **Status**: Active
- **Complexity**: Large
- **Risk triggers**: architecture_boundary, persistent_state, public_contract

## Outcome

Make canonical change execution task-backed and establish restart-durable MCP execution primitives without changing once-through workflow semantics.

## Authority and scope

- Work authority: `WORK-498` / GitHub issue #498.
- Repository authority: `AGENTS.md`, `SPEC.md`, applicable MCP 2026 task contracts and tests.
- Existing Work records, execution IDs, receipts, exact source identity, and fencing remain authoritative; MCP task IDs are transport-facing handles only.
- Change 626 owns startup/recovery scripts for #660 and is excluded from this change.

## Requirements

- **REQ-001**: `execute_change_workflow` must be task-backed so normal long execution does not occupy one HTTP request until transport failure.
- **REQ-002**: record whether each candidate `tools/call` actually advertises `io.modelcontextprotocol/tasks` without retaining request payloads.
- **REQ-003**: support a Redis/Valkey-backed Docket configuration with per-runtime-instance queues.
- **REQ-004**: when durable mode is enabled, the HTTP frontend must not execute queued task work; an independent worker owns execution.
- **REQ-005**: backend and worker launchers must fail closed and must never perform an implicit network pull.
- **REQ-006**: preserve current in-process task behavior while durable mode is disabled.
- **REQ-007**: retain synchronous compatibility surfaces for callers that cannot negotiate Tasks; durable-job fallback remains required if live host evidence proves Tasks unavailable.

## Acceptance

1. A task-capable call to canonical change execution receives a task handle and completes exactly once.
2. Boundary telemetry distinguishes Tasks-capable from non-Tasks tool calls.
3. Enabled frontend and worker processes share one instance-scoped durable queue while frontend worker concurrency is zero.
4. A task remains queryable after frontend replacement while the independent worker continues execution.
5. Operation and development runtimes cannot consume each other's task queues.
6. Missing/invalid runtime identity, role, backend configuration, or local image fails closed.
7. The live resilience test proves restart persistence against a real loopback Redis/Valkey backend before #498 can complete.
8. Existing once-through workflow shape remains unchanged.

## Risks and recovery

- A durable task record without an independent worker would preserve identity but not execution lifetime; durable mode therefore separates frontend and worker concurrency.
- Redis/Valkey loss may delay task delivery; Docket redelivery and KIS execution/fencing evidence remain the recovery authority.
- The backend launcher never pulls an image. Missing external artifacts block commissioning rather than weakening HR-002.
- Rollback is disabling `settings/task-runtime.settings.json` and reverting this governed change; default in-process behavior remains available.

## Out of scope

- Modifying #660-owned startup/recovery scripts while Change 626 is active.
- Making MCP task storage a replacement for Work Management or KIS execution receipts.
- Claiming live restart durability before a real Redis/Valkey commissioning run passes.
