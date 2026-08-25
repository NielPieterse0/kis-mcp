# FastMCP 4 / MCP 2026 Implementation Plan

**Goal:** Deliver Work #475 completely without touching kis-op.

**Architecture:** Keep KIS Work/execution/receipt/fencing state authoritative. Upgrade the MCP boundary to FastMCP 4, install the MCP Tasks extension, and apply optional task execution only to selected long-running KIS tools. Treat task/request/session metadata as transport/correlation state, not mutation authority. Drive progress through FastMCP Context and propagate cooperative cancellation into owned process execution where possible.

**Tech stack:** Python 3.13, FastMCP 4.0.0b3, fastmcp-tasks/Docket, MCP SDK v2, pytest, PowerShell governance/verification, existing KIS provider/proxy architecture.

## Global constraints

- Stay inside `scope.json`; keep scope current.
- Use tests before each new behavior change.
- Preserve HR-001/002/003, coordinator fencing, receipts, and existing authority boundaries.
- Do not activate or expose Supabase.
- Do not stop/restart/touch kis-op.
- Use local MCP 2026-07-28 corpus as protocol authority and record exact pages.
- No giant timeout/keepalive workaround may substitute for Tasks.

## Task 1 — Dependency and SDK migration

- Pin FastMCP 4 + tasks extra and explicit direct dependencies; regenerate lock.
- Replace removed/moved imports and snake_case SDK v2 surfaces.
- Update stateless request-boundary telemetry from initialize-era assumptions to modern discovery/per-request metadata.
- Focused evidence: import/telemetry/middleware/provider contract tests.

## Task 2 — MCP Tasks boundary

- Add one KIS-owned Tasks integration helper and stable `TaskConfig` for long operations.
- Install `TasksExtension` in gateway composition exactly once.
- Task-enable selected long-running tools while leaving fast bounded operations synchronous.
- Prove task-capable result discrimination and synchronous fallback.
- Prove task retrieval from a fresh client after the creating connection closes.

## Task 3 — Progress, deadlines, cancellation

- Add Context progress to selected task-capable operations at meaningful bounded stages.
- Preserve existing KIS execution deadlines; do not derive them from task TTL or request timeout.
- Add explicit stall/heartbeat semantics where existing long execution polling has enough evidence to distinguish stalled work.
- On cancellation of verification/owned process execution, attempt termination of the known process handle before propagating cancellation.
- Add red/green tests for progress visibility, deadline separation, cancellation, and completion/cancel races.

## Task 4 — 2026 wire/schema compatibility

- Remove stale FastMCP 3 camelCase runtime/test reads or document a specific legacy compatibility reason.
- Test JSON Schema 2020-12 tool schema output, snake_case SDK access, MCP wire aliases/resultType behavior, and ResourceLink/modern content acceptance.
- Validate request-scoped protocol/capability behavior and no session-derived durable authority.

## Task 5 — Provider/runtime acceptance

- Exercise FastMCP 4 provider/proxy disconnect/reconnect behavior on kis-dev-safe paths.
- Verify Supabase remains absent from tool, capability, provider-status, and normal user surfaces.
- Reconcile runtime composition and capability catalogue after Tasks wiring.

## Task 6 — Protocol evidence and deferred issues

- Record exact pages resolved from `000-index.md`, including schema authority `055-specification-schema-reference.md`.
- Map each relevant requirement to FastMCP-owned implementation, KIS-owned implementation, or explicit deferral.
- Create separate Work issues for every high-value deferred 2026 improvement with objective activation trigger.
- Update the smallest canonical current/operations documentation owners.

## Task 7 — Review, verification, publication, commissioning

- Run focused affected tests and Ruff/diff checks during development.
- Run `pwsh -File scripts/change-workflow.ps1 check`.
- Run required architecture, API-contract, code-quality, test-quality, documentation, and security reviews; fix blocking findings and re-review affected scope.
- Create a clean governed commit and publish via the registered GitHub route.
- Require exact-head GitHub Actions/canonical verification and Work merge-readiness.
- Merge only the authorized exact head.
- Verify live kis-dev FastMCP 4 behavior, Tasks reconnect/result retrieval, provider/proxy recovery, and Supabase absence after the landed restart hook.
- Complete Work #475, reconcile documentation evidence, and run governed cleanup from clean main.
