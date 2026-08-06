# Work Management Traceability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use Superpowers TDD and execute this plan task-by-task with review checkpoints.

**Goal:** Implement provider-neutral P3 traceability, merge-readiness evidence, and post-merge documentation reconciliation.

**Architecture:** Add one cohesive `traceability.py` domain module containing explicit immutable evidence contracts, deterministic validation, merge-readiness evaluation, and documentation milestone transformations. Extend `WorkRecord` only with traceability-required and documentation-milestone state; keep provider, gateway, workflow, CLI, CI, and reconciliation automation outside this slice.

**Tech Stack:** Python 3.11+, frozen slotted dataclasses, `StrEnum`, pytest, PowerShell repository governance scripts.

## Global constraints

- Stay inside `scope.json` and do not touch deferred change `040-context7-serena-adapters`.
- Preserve the provider-neutral `work_management` dependency boundary.
- Add every behavior through red-green-refactor TDD.
- Do not add a fourth HR policy rule or provider-specific identity.
- Keep all evidence deterministic, bounded, JSON-safe, and immutable.

---

### Task 1: Work-record traceability milestone state

**Files:**
- Modify: `src/kis_mcp/work_management/contracts.py`
- Modify: `tests/work_management/test_contracts.py`
- Modify: `src/kis_mcp/work_management/lifecycle.py`
- Modify: `tests/work_management/test_lifecycle.py`

**Interfaces:**
- Produces: `DocumentationMilestoneState`, `WorkRecord.traceability_required`, and `WorkRecord.documentation_milestone`.
- Produces lifecycle rejection reasons `documentation_reconciliation_due` and `documentation_reconciliation_unrecorded` for traceability-required records.

- [ ] Add failing contract tests for enum validation, JSON serialization, and traceability flags.
- [ ] Run focused contract tests and confirm the expected failures.
- [ ] Implement the minimal contract fields and serialization.
- [ ] Add failing lifecycle tests proving due and unrecorded reconciliation block `Done`.
- [ ] Run lifecycle tests and confirm the expected failures.
- [ ] Implement the minimal lifecycle checks while preserving non-traceability behavior.
- [ ] Run contract and lifecycle tests until green.

### Task 2: Explicit traceability evidence contracts

**Files:**
- Create: `src/kis_mcp/work_management/traceability.py`
- Create: `tests/work_management/test_traceability.py`

**Interfaces:**
- Produces: `PullRequestState`, `VerificationStatus`, `TraceabilityStage`, and `TraceabilityIssueKind`.
- Produces: `PullRequestEvidence`, `VerificationEvidence`, `MergeEvidence`, `CloseoutEvidence`, `DocumentationReconciliationEvent`, and `ImplementationTrace`.
- Every contract exposes `to_json_dict()` and validates stable project, record, change, revision, path, and numeric identities without provider-specific response fields.

- [ ] Write failing tests for valid serialization and invalid identities.
- [ ] Run the new test module and confirm imports fail because the module does not exist.
- [ ] Implement the smallest immutable evidence contracts and helpers.
- [ ] Run the evidence-contract tests until green.

### Task 3: Missing, stale, duplicated, and contradictory relationship detection

**Files:**
- Modify: `src/kis_mcp/work_management/traceability.py`
- Modify: `tests/work_management/test_traceability.py`

**Interfaces:**
- Produces: `TraceabilityIssue`, `TraceabilityReport`, and `evaluate_traceability(trace, stage, pull_request_number=None)`.
- Issue kinds are `missing`, `stale`, `duplicated`, and `contradictory`; output ordering is deterministic.

- [ ] Add failing tests for missing stage evidence and expected branch/worktree relationships.
- [ ] Add failing tests for duplicate PR, verification, merge, and documentation evidence.
- [ ] Add failing tests for stale verification and contradictory orphan or mismatched relationships.
- [ ] Run each test group and confirm behavior-specific failures.
- [ ] Implement deterministic evaluation for active, review, merge-ready, merged, and closed stages.
- [ ] Refactor only after all relationship tests are green.

### Task 4: Exact-revision merge readiness and documentation impact

**Files:**
- Modify: `src/kis_mcp/work_management/traceability.py`
- Modify: `tests/work_management/test_traceability.py`

**Interfaces:**
- Produces: `MergeReadiness` and `evaluate_merge_readiness(record, trace, pull_request_number)`.
- Required mode accepts only `pre_merge_complete` or reviewed `none`; advisory mode reports an advisory; off mode adds no documentation gate.
- A passing verification must target the exact selected pull-request head revision.

- [ ] Add failing tests for exact-head verification, stale verification, record/trace identity mismatch, and missing PR evidence.
- [ ] Add failing tests for required, advisory, and off documentation modes.
- [ ] Run merge-readiness tests and confirm expected failures.
- [ ] Implement minimal readiness aggregation from structured traceability findings and documentation state.
- [ ] Run all traceability tests until green.

### Task 5: Post-merge documentation reconciliation events

**Files:**
- Modify: `src/kis_mcp/work_management/traceability.py`
- Modify: `tests/work_management/test_traceability.py`
- Modify: `tests/work_management/test_lifecycle.py`

**Interfaces:**
- Produces: `create_documentation_reconciliation_due(trace, pull_request_number, documentation_task_id, required_updates)`.
- Produces: `complete_documentation_reconciliation(event, completion_revision)`.
- Produces: `apply_documentation_reconciliation_event(record, event)`.

- [ ] Add failing tests proving a merged PR creates the exact `documentation_reconciliation_due` event with required links.
- [ ] Add failing tests for mismatched project/specification identity and missing merge evidence.
- [ ] Add failing tests proving a due event moves verification work to `Documentation` and blocks `Done`.
- [ ] Add failing tests proving completion records a revision and permits `Done`.
- [ ] Implement the minimal pure transformations and rerun focused tests until green.

### Task 6: Package boundaries and programme reconciliation

**Files:**
- Modify: `src/kis_mcp/work_management/__init__.py`
- Modify: `tests/work_management/test_architecture.py`
- Modify: `.work/programmes/work-management/programme.json`
- Modify: `.work/programmes/work-management/roadmap.md`
- Modify: `.work/changes/053-work-management-traceability/tasks.md`

**Interfaces:**
- Public package exports include the new provider-neutral contracts and functions.
- Architecture file-set checks include only the new `traceability.py` unit and retain forbidden-import checks.
- Programme P3 status and remaining P4/P5 work remain explicit.

- [ ] Add failing export and architecture expectations before changing production exports.
- [ ] Update exports and programme status with no reader-facing runtime claim.
- [ ] Run the complete work-management suite.

### Task 7: Verification, review, and delivery

**Files:**
- Modify: `.work/changes/053-work-management-traceability/closeout.md`
- Modify: `.work/changes/053-work-management-traceability/tasks.md`

- [ ] Run `pwsh -NoProfile -File scripts/change-workflow.ps1 check`.
- [ ] Run focused tests and `pwsh -NoProfile -File scripts/verify.ps1`.
- [ ] Review specification, plan, implementation, tests, and evidence together; fix all blocking findings and rerun affected checks.
- [ ] Record exact verification and review evidence in closeout.
- [ ] Commit, push, open the pull request, inspect CI and review threads, and merge only if current evidence is clean.
- [ ] Mark governance closed, run governed cleanup from clean `main`, and verify the deferred `040` worktree is unchanged.
