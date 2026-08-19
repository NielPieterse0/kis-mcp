# Housekeeping Source Inventory Implementation Plan

**Goal:** Remove repository-history-dependent source-read exhaustion without weakening Change 194 evidence semantics.

**Architecture:** Keep the existing runner state machines. For absent governed issue bindings, obtain a bounded cursor-complete inventory of open repository issues and use it only after completeness is proven. Fall back to the existing exact source reads when that inventory cannot be proven complete. In backlog readiness, reuse successful exact dependency states within one run only.

**Tech Stack:** Python 3.11+, existing KIS operation invoker, GitHub MCP provider, pytest, Ruff.

## Global constraints

- Stay inside `scope.json`.
- Preserve preview-only unattended scheduling and all apply gates.
- Preserve fail-closed behavior when source evidence is incomplete.
- Preserve legacy status/metadata/dependency semantics; do not infer modern metadata onto historical records.
- Do not touch Change 195 or repository residue.

### Task 1 — Reproduce scaling defects

- Add a reconciliation test where historical closed bindings exceed the exact-read budget but a complete open-source inventory fits.
- Add a backlog test where two records share one exact dependency and a one-read budget must suffice.
- Confirm both tests fail against the pre-change runner behavior.

### Task 2 — Optimize authoritative evidence reads

- Add bounded cursor-complete open-issue inventory acquisition.
- Use it only for issue source kinds and only after complete pagination is proven.
- Retain exact source-read fallback for unavailable/incomplete inventory evidence and other source kinds.
- Add successful per-run dependency-state caching without caching failures.

### Task 3 — Verify and deliver

- Run focused housekeeping/runtime tests, Ruff, diff checks, and governed scope check.
- Run required specialist reviews on the complete base→candidate range and resolve blocking findings.
- Freeze one final head, publish PR, obtain canonical GitHub Actions on that exact head, merge, restart/refresh `kis-op`, and require fresh unattended complete receipts for both runners before reconciling #379/#364.