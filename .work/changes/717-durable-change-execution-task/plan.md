# Durable Change Execution Task Implementation Plan

**Goal:** Complete WORK-498 as one governed change without altering once-through semantics or #660-owned startup/recovery surfaces.

**Architecture:** Keep KIS Work/execution/fencing authoritative. Use MCP Tasks for transport-facing long calls, Docket + loopback Redis/Valkey for restart-persistent handles, and a separate worker process when durable mode is enabled. Frontends publish/query tasks only.

## Constraints

- Stay inside `scope.json`.
- Do not restart or mutate `kis-op`.
- Do not overlap Change 626 startup/recovery paths.
- Do not pull external images through local process execution.
- Full repository verification remains exact-head CI authority.

## Implementation sequence

1. Task-enable canonical `execute_change_workflow` and prove handle creation/retrieval/exactly-once execution.
2. Add request-scoped Tasks-negotiation observability.
3. Add validated durable task-runtime settings and instance/role queue fencing.
4. Add independent worker and local-only backend launchers.
5. Add real Redis/Valkey frontend-restart resilience test, skipped only when the commissioning backend is absent.
6. Commission the pinned backend through an approved external-artifact path; run the live resilience test.
7. Observe the live ChatGPT host Tasks capability; implement durable-job fallback only if Tasks are unavailable.
8. Run focused checks, governance check, review, exact-head CI, merge, and cleanup.
