# Post-Merge Project Field Commissioning Implementation Plan

**Goal:** Add a scoped canonical field-only path to the existing registered Project commissioner without weakening full-schema safety.

**Architecture:** Reuse the existing manifest, registry target resolution, approval gate, GitHub GraphQL client, and schema comparison semantics. Factor field preflight/apply/verify logic so both modes share one implementation. Full mode performs the existing complete view preflight before invoking shared field mutation and then continues existing view commissioning. Fields mode stops after canonical field verification and never enters view mutation/preflight logic.

**Tech Stack:** Python 3.13, FastMCP capability descriptors, GitHub CLI/GraphQL through the existing registered client, pytest, repository change governance.

## Global constraints

- Stay inside `scope.json`; no housekeeping, #409, #437, or general Work Management changes.
- Tests first for each new behavior.
- `scope` is fixed to `full|fields`; default remains `full`.
- No caller-supplied field names or provider query payloads.
- Preserve approval requirements and full-mode mutation ordering/safety.
- A fields-only result cannot imply full view/schema readiness.

### Task 1: Lock the safety contract with failing tests

**Tests:** `tests/providers/github/projects/test_schema_commissioning.py`

- Add a test proving fields mode provisions missing manifest fields despite unrelated unsupported view sort/group drift and emits no view mutation.
- Add a test proving a deterministic field blocker refuses fields mode before mutation.
- Retain the existing full-mode `test_commission_preflights_all_view_refusals_before_any_mutation` unchanged in meaning.
- Run focused provider commissioning tests and confirm new tests fail before implementation.### Task 2: Implement shared field commissioning

**Source:** `src/kis_mcp/providers/github/projects/schema_commissioning.py`

- Extract deterministic field preflight from the full commissioner.
- Extract field create/option-update/re-read verification into a shared bounded helper.
- Add fields-only entry path that executes field preflight and shared field apply only.
- Preserve full commissioner's preflight of all unsupported view mutations before the first field mutation.
- Return explicit scoped readiness/evidence without claiming view readiness for fields mode.

### Task 3: Extend the existing registered operation contract

**Source:** `src/kis_mcp/projects/github_exact.py`, `src/kis_mcp/capabilities/surface.py`
**Tests:** `tests/projects/test_github_exact.py`, `tests/capabilities/test_registered_commit_workflow.py`, `tests/capabilities/test_exposure_execution.py`

- Add optional `scope` enum `full|fields` to the existing operation schema and dispatcher.
- Default omitted scope to `full` for compatibility.
- Keep the operation virtual, discoverable, external, and approval-gated.
- Assert arbitrary inputs and unknown scopes remain rejected.

### Task 4: Reconcile normative documentation and verify

**Documentation:** `SPEC.md`

- Describe the section-bounded canonical Project commissioner without reviving remote-branch deletion or generic Project administration.
- Run focused provider/projects/capability suites, `git diff --check`, and `change-workflow.ps1 check`.
- Run required code-quality, architecture, and API-contract reviews; resolve actionable findings.
- Run full `scripts/verify.ps1`, commit, publish exact-head PR, require canonical Actions, merge-readiness, merge, documentation closeout, and cleanup.
- After merge/runtime refresh, invoke `scope=fields` live and re-read Project schema status as #419 commissioning evidence.