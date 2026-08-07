# Work Management Review Evidence Implementation Plan

> **For agentic workers:** Execute task-by-task with red-green TDD. Keep all edits inside `scope.json` and preserve the internal-only P4 boundary.

**Goal:** Implement provider-neutral review-run evidence, explicit coverage, observation triage, finding extraction, and finding lifecycle contracts.

**Architecture:** Add one cohesive `work_management/reviews.py` module. It owns immutable JSON-safe domain contracts and deterministic pure functions. It validates canonical `.work/reviews/<REV-id>/` artifact manifests but performs no filesystem or provider operations.

**Tech Stack:** Python 3.11+, frozen dataclasses, `StrEnum`, standard library only, pytest.

## Global constraints

- Do not import FastMCP, gateway, providers, workflows, or GitHub-specific layouts from `work_management`.
- Do not modify policy, settings, public gateway composition, providers, the advisory agent, CLI, CI, or remote state.
- Do not create review artifact directories or implement persistence.
- Every production behavior starts with a failing focused test.
- All public values serialize to deterministic JSON-safe dictionaries.
- Preserve project identity and stable record-type prefixes.

---

### Task 1: Review identity, target, request, and coverage contracts

**Files:**
- Create: `tests/work_management/test_reviews.py`
- Create: `src/kis_mcp/work_management/reviews.py`

**Interfaces:**
- Produces enums `ReviewType`, `ReviewStatus`, `ExtractionMode`, and immutable contracts `ReviewTarget`, `ReviewBudget`, `ReviewRequest`, `ReviewCoverage`.
- All contracts expose `to_json_dict()`.

- [ ] Write failing tests for valid exact-commit requests, required `REV-` identity, repository validation, bounded path normalization, target-selector requirements, tuple uniqueness, positive budgets, and partial coverage serialization.
- [ ] Run `python -m pytest tests/work_management/test_reviews.py -q` and confirm collection fails because `reviews.py` does not exist.
- [ ] Implement only the enums, validation helpers, and four contracts required by those tests.
- [ ] Run the focused tests until green.
- [ ] Refactor duplicated validation only while the focused tests remain green.

### Task 2: Evidence manifest and normalized review result

**Files:**
- Modify: `tests/work_management/test_reviews.py`
- Modify: `src/kis_mcp/work_management/reviews.py`

**Interfaces:**
- Produces `ReviewArtifactKind`, `ReviewArtifact`, `ReviewEvidenceManifest`, `ReviewObservation`, `ObservationDisposition`, and `ReviewResult`.
- Produces `create_review_evidence_manifest(review_id: str, *, include_sarif: bool = False) -> ReviewEvidenceManifest`.

- [ ] Add failing tests for canonical `.work/reviews/<REV-id>/` paths, optional SARIF, repository-relative path rejection, explicit observation disposition, result identity consistency, incomplete-coverage visibility, and deterministic serialization.
- [ ] Run only the new tests and confirm expected failures for missing contracts/functions.
- [ ] Implement the minimum immutable artifact, observation, manifest, and result contracts.
- [ ] Run all review tests until green.
- [ ] Verify repeated manifest creation returns equivalent values and never touches the filesystem.

### Task 3: Extraction policy and deterministic child candidates

**Files:**
- Modify: `tests/work_management/test_reviews.py`
- Modify: `src/kis_mcp/work_management/reviews.py`

**Interfaces:**
- Produces `ExtractedReviewRecord`.
- Produces `extract_review_records(result: ReviewResult, mode: ExtractionMode) -> tuple[ExtractedReviewRecord, ...]`.

- [ ] Add failing tests proving `report_only` returns no candidates and informational/rejected/recommendation observations never auto-create durable records.
- [ ] Add failing tests proving `validated_findings` emits only validated `FINDING` or `SECURITY_FINDING` candidates.
- [ ] Add failing tests proving `full_governance` emits disposition-compatible finding, decision, assumption, risk, hold, and deferred-task candidates.
- [ ] Add failing tests for deterministic ordering, stable deduplication keys, repeated extraction equivalence, source-review/source-observation provenance, and project identity.
- [ ] Implement the smallest disposition-to-record mapping and deterministic key generation needed to pass.
- [ ] Run all review tests until green and remove any extraction behavior not required by the specification.

### Task 4: Finding lifecycle and evidence preservation

**Files:**
- Modify: `tests/work_management/test_reviews.py`
- Modify: `src/kis_mcp/work_management/reviews.py`

**Interfaces:**
- Produces `FindingState`, `FindingDetails`, `FindingRecord`, `FindingTransitionDecision`, and `FindingTransitionRejected`.
- Produces `evaluate_finding_transition(record: FindingRecord, target: FindingState) -> FindingTransitionDecision`.
- Produces `transition_finding(record: FindingRecord, target: FindingState) -> FindingRecord`.

- [ ] Add failing tests for the declared finding lifecycle, terminal states, rejected invalid jumps, and unchanged records after rejection.
- [ ] Add failing tests requiring source evidence, location, confidence, severity, validation disposition, remediation record, fix PR, and follow-up verification at the applicable states.
- [ ] Implement deterministic transition rules and state-specific prerequisites.
- [ ] Run all review tests until green.
- [ ] Confirm finding and security-finding record prefixes match their `WorkRecord` types.

### Task 5: Package integration and architecture boundary

**Files:**
- Modify: `src/kis_mcp/work_management/__init__.py`
- Modify: `tests/work_management/test_architecture.py`
- Modify: `tests/work_management/test_reviews.py`

**Interfaces:**
- Exports the approved P4 contracts and functions from `kis_mcp.work_management`.

- [ ] Add failing package-export tests and update the architecture expected-file set to include `reviews.py`.
- [ ] Run focused architecture and review tests and confirm expected failures.
- [ ] Add explicit package exports without introducing platform imports.
- [ ] Run `python -m pytest tests/work_management -q` until green.

### Task 6: Programme reconciliation, review, and verification

**Files:**
- Modify: `.work/programmes/work-management/programme.json`
- Modify: `.work/programmes/work-management/roadmap.md`
- Modify: `.work/programmes/work-management/target-spec.md`
- Modify: `.work/changes/055-work-management-review-evidence/tasks.md`
- Modify: `.work/changes/055-work-management-review-evidence/closeout.md`

- [ ] Update the programme authority to mark P4 implemented internally and P5 planned; resolve `PM-OPEN-002` with the manifest-only EvidenceStore decision.
- [ ] Run `pwsh -NoProfile -File scripts/change-workflow.ps1 check`.
- [ ] Run `git diff --check`.
- [ ] Run the focused work-management suite.
- [ ] Run `pwsh -NoProfile -File scripts/verify.ps1`.
- [ ] Perform findings-first review of the full specification, plan, code, tests, and documentation; fix substantiated findings and rerun affected checks.
- [ ] Record exact verification, residual limitations, recovery, and deferred P5 scope in closeout.
- [ ] Set the claim to `ready`, commit, push, and create a PR.
- [ ] Shepherd the PR to verified readiness. Request explicit landing confirmation for the exact ready head before any merge action.
