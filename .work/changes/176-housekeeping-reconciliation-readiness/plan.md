# Housekeeping Reconciliation Readiness Implementation Plan

**Goal:** Land a provider-neutral housekeeping foundation with Work Management reconciliation and backlog readiness runners.

**Architecture:** A typed housekeeping state-machine layer composes the existing KIS capability router. It reads authoritative Project/GitHub/local change evidence, emits bounded findings/actions/metrics, and invokes existing idempotent Work Management mutation gates only in explicit apply mode. The CLI is a host-neutral process contract; no scheduler or Windows executor is introduced.

**Tech Stack:** Python 3.11+, FastMCP in-process server surface, existing KIS Work Management/GitHub provider operations, pytest.

## Global constraints

- Stay inside `scope.json` and all operator exclusions.
- No LLM mutation authority or semantic guessing.
- Do not merge while canonical GitHub Actions exact-head CI is unavailable.
- Treat local verification as evidence, never as a substitute for required CI.

### Task 1: Typed trigger/receipt contract

- [x] Define manual/scheduled-neutral triggers and apply idempotency requirements.
- [x] Define typed findings, actions, metrics, conflicts, and receipts.
- [x] Add deterministic governed-change source binding reader.

### Task 2: Work Management reconciliation runner

- [x] Fail closed on truncated inventory.
- [x] Detect exact missing Project records and unique governed source bindings.
- [x] Detect lifecycle, ownership, readiness metadata, and Change ID projection drift.
- [x] Auto-plan/apply only exact missing-record capture through existing reconciliation.

### Task 3: Backlog readiness/dependency runner

- [x] Reuse `project_management_next_work` for deterministic executable-leaf selection.
- [x] Detect Blocked-without-dependency and dependency-without-blocked-state drift.
- [x] Resolve only strict exact dependency references; type semantic text as ambiguity.
- [x] Delegate Ready correction to `project_management_transition_work` preview/apply.

### Task 4: Host-neutral trigger surface

- [x] Add `scripts/housekeeping.py` with preview/apply and manual/scheduled trigger inputs.
- [x] Keep execution-provider and scheduler concerns outside runner semantics.

### Task 5: Verify and prepare

- [x] Run focused tests and compile/help checks.
- [x] Run governed scope check and selected local verification; record canonical-verification limitation.
- [x] Run specialist reviews and resolve the material bounded-read finding.
- [ ] Commit a clean candidate and prepare/queue a PR if gates permit.
- [x] Do not merge until canonical exact-head GitHub Actions evidence is available.
