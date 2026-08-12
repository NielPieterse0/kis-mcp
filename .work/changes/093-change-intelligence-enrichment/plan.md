# Change Intelligence Enrichment Implementation Plan

> Execute task-by-task in this isolated worktree; tests precede behavior changes and each final edit invalidates affected review/verification evidence.

**Goal:** Strengthen existing Discover change understanding without adding a competing subsystem.

**Architecture:** Keep `PlanChangeService` as the pre-change composer, `ContextBrokerService` as bounded task context, and `ImpactGraphService`/`AnalyzeChangeService` as actual-change analysis. Extend their typed contracts additively. Reuse the persistent Code/Symbol/Relationship intelligence and optional semantic evidence. Keep all findings advisory and non-executable.

**Tech Stack:** Python 3.11–3.13, stdlib AST/Git-backed Discover evidence, FastMCP contracts, JSON Schema, pytest, PowerShell repository verification.

## Global constraints

- Stay inside `scope.json`; never edit `policy/**`.
- Preserve exactly HR-001/HR-002/HR-003 and Discover read-only boundaries.
- Do not add dependencies or execute repository-discovered commands in Discover.
- Keep direct evidence ahead of transitive/heuristic evidence and reuse configured budgets.
- No unrelated worktree, branch, provider, runtime, or generated state may be changed.

### Task 1 — Contract-first reconciliation and replacement evidence

**Files:** `change_analysis.py`, analyze-change schemas, `test_analyze_change_workflow.py`.

- [ ] Add failing tests for optional planned-path reconciliation and replacement candidates.
- [ ] Extend request/response records and JSON schemas additively.
- [ ] Derive replacement candidates only from deleted/renamed status plus retained deterministic references.
- [ ] Confirm focused schema/workflow tests pass.

### Task 2 — Blast radius and support surfaces

**Files:** `impact_contracts.py`, `impact_graph.py`, inspect-impact schema, `test_impact_graph.py`.
- [ ] Add failing tests for bounded transitive imports and documentation/configuration/contract/policy relationships.
- [ ] Add medium-confidence transitive import evidence after direct edges.
- [ ] Generalize support-surface relationships with explicit kind/provenance and existing dependant budget.
- [ ] Preserve affected-test and verification handoff behavior.

### Task 3 — Context and planning enrichment

**Files:** `context_broker.py`, `planning.py`, `planning_contracts.py`, `tools.py`, `test_context_broker.py`, `test_plan_change.py`.

- [ ] Add failing tests for related support-artifact retention and `REUSE/EXTEND/REPLACE/NEW` plan guidance.
- [ ] Enrich selected context with bounded support artifacts tied to selected implementation tokens.
- [ ] Add planned paths and pattern records to `plan_change`; keep execution false.
- [ ] Route optional planned reconciliation arguments through `analyze_change` tool registration.

### Task 4 — Authority/status reconciliation

**Files:** `docs/DISCOVER-MODULE-PRODUCT-SPEC.md`, `SPEC.md`.

- [ ] Update current implementation claims only after focused behavior is green.
- [ ] State new evidence as advisory Discover output, not Govern or Work policy.

### Task 5 — Final gate

- [ ] Run all focused Discover tests and JSON-schema validation.
- [ ] Run `pwsh -File scripts/change-workflow.ps1 check` and `git diff --check`.
- [ ] Run canonical `pwsh -File scripts/verify.ps1`.
- [ ] Run independent code-quality and safety/security review on the exact final worktree; resolve blocking findings and rerun affected gates.
- [ ] Commit exact final state, publish to a dedicated branch, create/verify PR, merge exact approved head, then clean only 093 from refreshed primary `main`.
