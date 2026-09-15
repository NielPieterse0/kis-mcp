# Tasks: Durable Change Execution Task

- [x] Confirm authority, WORK-498 binding, and non-overlapping scope.
- [x] Make canonical change execution require MCP Tasks.
- [x] Prove task handle creation, polling, completion, and exactly-once execution.
- [x] Record per-call Tasks negotiation in bounded runtime observability.
- [x] Add durable Docket runtime settings with instance/role queue fencing.
- [x] Add independent task worker launcher.
- [x] Add local-only pinned Valkey backend launcher that never pulls.
- [x] Add live frontend-restart/independent-worker resilience test.
- [ ] Acquire/commission the pinned Valkey image through an approved external path.
- [ ] Run the live Redis/Valkey resilience test without skip.
- [x] Preserve an explicit synchronous `execute_change_workflow_sync` compatibility surface without weakening the canonical Tasks-required path.
- [ ] Observe live ChatGPT Tasks negotiation and decide whether a durable-job façade is required beyond the synchronous compatibility surface.
- [ ] Reconcile FastMCP stable-version hardening if required for this execution slice.
- [ ] Run focused verification and `scripts/change-workflow.ps1 check`.
- [ ] Record review/closeout evidence and update the existing PR exact head.
- [ ] Pass exact-head CI, merge, and run safe cleanup from `main`.
