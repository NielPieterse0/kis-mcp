# FastMCP 4 Proxy Loop Startup Implementation Plan

> **For agentic workers:** Execute task-by-task and keep scope/evidence current.

**Goal:** Restore `kis-dev` startup without touching `kis-op`.

**Architecture:** Stop enumerating the actual aggregate proxy graph during synchronous composition. Snapshot tools only from provider subtrees that contain no proxy provider, discover Desktop Commander through a separate `keep_alive=False` proxy, and retain approved mounted-provider operations from their declared provider contracts plus live runtime probes.

**Tech Stack:** Python 3.13, FastMCP 4.0.0b3, pytest, KIS change workflow.

## Global constraints

- Stay inside Change 240 scope.
- Add regression coverage before behavior changes.
- Do not stop/restart/reconfigure `kis-op`.
- Do not change dependency versions or provider activation.
- Preserve Work #475 behavior and capability/exposure semantics.

### Task 1 — Reproduce and pin the loop-lifecycle defect

**Requirements:** REQ-001, REQ-004

- Modify: `tests/capabilities/test_gateway_composition.py`
- [x] Add a test that fails if composition calls aggregate `server.list_tools()` on the actual runtime server.
- [x] Prove the test fails against the pre-fix implementation.
### Task 2 — Separate construction-time discovery from live proxies

**Requirements:** REQ-001, REQ-002, REQ-003

- Modify: `src/kis_mcp/gateway/composition.py`
- Test: `tests/capabilities/test_gateway_composition.py`
- [x] List tools only from provider subtrees that contain no `ProxyProvider`, preserving internal KIS mounted subservers without touching live proxies.
- [x] Discover Desktop Commander using a separate stdio proxy with `keep_alive=False`.
- [x] Project declared operations for mounted platform providers without enumerating their live proxy servers.
- [x] Keep dynamic `provider_runtime_tools(...)` refresh for runtime-discovered schemas/tools.

### Task 3 — Verify behavior and operational recovery

**Requirements:** REQ-002, REQ-004, REQ-005

- [x] Run focused capability/gateway/provider tests and repository-configured Python verification (Ruff is not configured in this repository environment).
- [x] Run governed change check and resolve the selected verification handoffs with focused local evidence; exact-head full verification remains PR-owned.
- [x] Review the exact diff for architecture, code quality, and test quality.
- [x] Start only `kis-dev` and prove readiness while recording unchanged `kis-op` identity.
- [ ] Publish, obtain exact-head CI/readiness, merge through the governed path, refresh `main`, and re-commission `kis-dev`.
- [ ] Complete Work #475 and clean Change 240 only after live merged-main evidence passes.
