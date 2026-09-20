# Tasks: Durable Change Execution Task

- [x] Confirm authority, WORK-498 binding, and non-overlapping scope.
- [x] Make canonical long operations use MCP Tasks when advertised and transparently fall back synchronously otherwise.
- [x] Prove task handle creation, polling, completion, and exactly-once execution.
- [x] Record per-call Tasks negotiation in bounded runtime observability.
- [x] Add durable Docket runtime settings with instance/role queue fencing.
- [x] Add independent task worker launcher.
- [x] Add local-only pinned Valkey backend launcher that never pulls.
- [x] Add live frontend-restart/independent-worker resilience test.
- [ ] Acquire/commission the pinned Valkey image through an approved external path.
- [ ] Run the live Redis/Valkey resilience test without skip.
- [x] Preserve explicit synchronous compatibility aliases without requiring callers to choose them.
- [x] Observe live ChatGPT Tasks negotiation: current host invocation omitted Tasks capability; make canonical long operations transparently fall back synchronously without exposing transport choice as workflow ceremony.
- [x] Confirm no FastMCP version change is required for this slice; the observed defect is capability routing, not a dependency-version failure.
- [x] Run focused verification and `scripts/change-workflow.ps1 check`.
- [ ] Record review/closeout evidence and update the existing PR exact head.
- [ ] Pass exact-head CI, merge, and run safe cleanup from `main`.
