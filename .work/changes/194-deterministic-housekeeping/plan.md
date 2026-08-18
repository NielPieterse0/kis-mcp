# Deterministic Housekeeping Implementation Plan

**Goal:** Restore the retained deterministic housekeeping value from PR #327 against the current provider and Work Management contracts without replaying historical commits.

**Architecture:** Add one isolated `kis_mcp.housekeeping` package containing typed trigger/receipt contracts, governed local source-binding discovery, an operation-invoker boundary, and two deterministic runners. A host-neutral CLI constructs the current KIS server and invokes the same runners. All external mutations remain delegated to existing Work Management gates.

**Tech Stack:** Python 3.11+, FastMCP 3.x runtime surface, current KIS Work Management/GitHub operations, pytest, Ruff.

## Global constraints

- Stay inside `scope.json`; do not touch execution or Actions workflow paths.
- Use MCP/KIS operations as composed authorities instead of duplicating mutation logic.
- Add focused tests before implementation and prove the expected initial failure.
- No semantic guessing, direct Project field writes, scheduler, or LLM mutation authority.

### Task 1 — Contracts and governed evidence

- Add typed trigger/finding/action/receipt contracts with bounded apply semantics.
- Add deterministic `.work/changes/*/scope.json` source-binding discovery.
- Test invalid apply/scheduled triggers and exact local source binding.

### Task 2 — Reconciliation runner

- Read bounded authoritative Project inventory and fail closed on truncation.
- Detect missing governed records and operational/projection drift.
- Verify missing sources through current `github_issue_read` and compose exact Project reconciliation only for unique open bindings.
- Suppress all apply actions when source-evidence completeness is lost.

### Task 3 — Backlog readiness runner

- Reuse current `project_management_next_work` for canonical selection evidence.
- Distinguish absent, exact, resolved, and ambiguous dependency evidence.
- Preview `blocked -> ready` only through `project_management_transition_work`; never clear `Blocked By` directly.

### Task 4 — CLI and verification

- Add provider-neutral `scripts/housekeeping.py` for manual/scheduled preview/apply execution.
- Run focused tests, Ruff/compile/help, and governed scope check.
- Run required full-range specialist reviews before publication; fix findings and rerun only affected checks.
- Freeze the final head, publish/open PR, obtain one canonical GitHub Actions run for that exact SHA, then merge/reconcile/cleanup.
