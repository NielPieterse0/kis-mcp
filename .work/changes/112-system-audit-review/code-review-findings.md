# Systematic Code Review Findings

## Baseline

Audit target: current local tree `52465b2`. Canonical `scripts/verify.ps1` passed: full pytest exit 0, two expected skips, 277 Python files syntax-checked, configuration/dependencies/change-governance and HR-001/002/003 green. No product file was modified.

Additional read-only checks included Ruff, AST size/branch scanning, import/coupling scans, TODO/FIXME search, effect-sensitive primitive search, live provider status, live capability discovery, and focused code inspection.

## Findings

**CR-01 | Provider commissioning status is hard-coded stale | Severity: High.** `dbhub/provider.py::_commissioning()` and `dockerhub/provider.py::_commissioning()` always return `upstream_connected/tools_discovered=pending_live_verification` and `live_verified=pending` whenever installed. Both live `kis-dev` and `kis-op` therefore instruct the user to commission providers that change 111 already commissioned successfully. Closure: persist or deterministically derive commissioned evidence and make status distinguish “commissioned evidence exists” from “current-process live probe not run.”

**CR-02 | Enabled Python SDK provider is inert | Severity: Medium.** `settings/providers/python-sdk.provider.json` has `enabled=true`; `providers/python_sdk/**` is implemented/tested, but `providers/platform.py` never registers it and repository search finds no non-test consumer. Change 044 explicitly deferred composition and no later slice completed it. Closure: choose an explicit staged/inactive/current lifecycle and align settings/runtime accordingly.

**CR-03 | Deprecated FastMCP transformation API | Severity: Medium-Low.** `providers/dockerhub/adapter.py:48` uses `add_tool_transformation`; canonical tests emit repeated FastMCP 3.4.4 deprecation warnings recommending `add_transform(ToolTransform(...))`. Current behavior passes, but a future FastMCP upgrade can break this adapter. Closure: migrate through a focused compatibility slice with exact public-tool regression tests.

**CR-04 | Static-quality debt is outside the canonical gate | Severity: Medium-Low.** Ruff reports 43 issues: 20 F401, 15 E402, 4 F402, 2 E702, 1 F821 and 1 F841, while canonical verification remains green. Concrete examples include the unused `targets` computation in `discover/impact_graph.py` and undefined `Mapping` annotation in a test. Closure: first clean concrete defects/hygiene, then decide whether a bounded lint profile belongs in canonical or advisory verification.
**CR-05 | Oversized deterministic evaluators increase review cost | Severity: Low-Medium.** AST scan found `work_management.traceability.evaluate_traceability` at 378 lines/47 branch nodes, `discover.service.inspect` at 325 lines, and several Discover analyzers/builders around 188–250 lines. No failing behavior was found and the functions are mostly linear contract evaluation. Closure: simplify only along repeated independent change reasons; avoid a broad rewrite.

**CR-06 | Govern implementation is complete enough to be maintained but unreachable | Severity: Medium.** `src/kis_mcp/govern/**`, six enabled governance rules, settings/schema and tests exist; four FastMCP tool registrations are implemented, but gateway composition and capability discovery never include them. This is not a current runtime regression because current architecture still labels Govern target-state, but it is substantive dormant code. Closure: explicitly complete or stage the integration rather than leaving an enabled-looking subsystem in an ambiguous state.

## Non-findings / controls checked

- No unresolved TODO/FIXME/HACK/XXX marker was found in current source/tests/scripts/current docs.
- The apparent `shell=True` hit is an intentionally vulnerable code snippet embedded in the review-backend benchmark prompt, not executed repository code.
- Hard-rule register test names all resolve to concrete tests, and canonical policy verification passed.
- Long-lived launcher stdout/stderr buffering identified in historical change 013 is no longer current: `start-chatgpt.ps1` drains owned process jobs repeatedly during readiness and steady-state loops.
- Broad exception catches are concentrated at provider/process/tool boundaries and generally convert failures into typed readiness or diagnostic states; no evidence-backed silent security bypass was found.

## Review judgment

No presently failing core safety/correctness defect was found beyond the provider commissioning-status misreport. The repository has strong test coverage and fail-closed policy behavior; the main engineering debt is stale runtime status semantics, dormant integration surfaces, deprecation debt, and localized complexity/static hygiene.