# P5 Work Management Automation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Deliver durable evidence, deterministic reconciliation, GitHub adaptation, CLI/CI automation, portfolio status, and platform workflow composition for P5.

**Architecture:** Keep domain persistence, reconciliation, settings, service, and status provider-neutral. Isolate GitHub tool names and response layouts in `providers/github/project_management.py`. Expose task-level workflows through `workflows/project_management` and the existing 047 contribution surface.

**Tech stack:** Python 3.11 stdlib, dataclasses, strict JSON, FastMCP 3.4.4, PowerShell wrappers, pytest, GitHub Actions YAML.

## Global constraints

- Preserve exactly HR-001, HR-002, and HR-003.
- Write only beneath `C:\Projects`; never permanently delete artifacts.
- No generic GraphQL passthrough, external database, or silent provider installation.
- Remote mutations default to preview and require explicit apply plus idempotency.
- Provider-neutral modules must not import FastMCP or provider layouts.
- Every task maps to requirements and produces focused test evidence.

---

### Task 1: Settings and modularity baseline

**Requirements:** REQ-P5-001, REQ-P5-010, REQ-P5-012

**Files:** create `work_management/settings.py`, JSON settings/schema, and focused tests; update architecture enforcement.

- [ ] Add failing tests for strict keys, project/binding identity, feature/automation/gate enums, duplicate rejection, and multi-project attribution.
- [ ] Implement immutable settings contracts and loader.
- [ ] Record measured module evidence and confirm the planned seams remain reversible.
- [ ] Run focused settings and architecture tests; commit independently.

### Task 2: Atomic evidence persistence

**Requirements:** REQ-P5-002, REQ-P5-010, REQ-P5-012

**Files:** create `work_management/evidence.py`; extend review exports and tests.

- [ ] Add failing tests for manifest validation, atomic write, idempotent replay, hash conflict, bounded payloads, path containment, and retained prior content.
- [ ] Implement `ReviewEvidenceStore` with temporary sibling files and `os.replace`.
- [ ] Implement read/inspect results without mutation and no delete surface.
- [ ] Run focused evidence tests; commit independently.

### Task 3: Reconciliation, service, and portfolio status

**Requirements:** REQ-P5-003, REQ-P5-004, REQ-P5-006, REQ-P5-010

**Files:** create `reconciliation.py`, `service.py`, `status.py`; update package exports and tests.

- [ ] Add failing tests for deterministic action planning, conflicts, partial/inaccessible observations, per-record results, dry-run, and two-project summaries.
- [ ] Implement provider-neutral desired/observed contracts and optimistic-concurrency decisions.
- [ ] Implement the application facade and bounded portfolio status aggregation.
- [ ] Run focused domain tests; commit independently.

### Task 4: GitHub project adapter

**Requirements:** REQ-P5-005, REQ-P5-010, REQ-P5-012

**Files:** create `providers/github/project_management.py`; add provider tests and capability metadata.

- [ ] Add failing contract tests for capability detection, pagination completeness, stable identities, response normalization, redacted errors, idempotency, preview/apply, and conflict tokens.
- [ ] Implement a narrow adapter over injected fixed-shape GitHub operations.
- [ ] Exclude delete and arbitrary GraphQL operations; isolate provider failures.
- [ ] Run provider tests; commit independently.

### Task 5: CLI, CI, and workflow composition

**Requirements:** REQ-P5-007, REQ-P5-008, REQ-P5-009, REQ-P5-010

**Files:** create `scripts/project_workflow.py`, `scripts/project-workflow.ps1`, `.github/workflows/work-management.yml`, and `workflows/project_management/**`; update `workflows/platform.py` and tests.

- [ ] Add failing CLI tests for fixed commands, bounded JSON, structured exit codes, exact revision, dry-run defaults, and apply/idempotency requirements.
- [ ] Add workflow tests for task-level descriptors, bounded operations, capability prerequisites, and isolated registration failure.
- [ ] Implement settings/status/inventory/reconcile/verify-traceability CLI commands and reusable CI gates.
- [ ] Register P5 workflow descriptors and platform operations without delete or raw provider passthrough.
- [ ] Run CLI, workflow, YAML, and architecture checks; commit independently.

### Task 6: Documentation, review, commissioning, and closeout

**Requirements:** REQ-P5-011, REQ-P5-012

**Files:** update programme authority, README, SPEC, platform concept, operations, and change artifacts.

- [ ] Reconcile current-versus-target implementation statements and mark P5 implemented only to verified boundaries.
- [ ] Run change scope check, focused suites, `git diff --check`, and canonical `scripts/verify.ps1`.
- [ ] Perform findings-first automated and direct review; fix blocking findings and rerun affected checks.
- [ ] Verify GitHub authentication, repository access, configured capabilities, and live read-only commissioning; state unsupported remote Project operations explicitly.
- [ ] Push, open PR, review exact head, merge only after explicit operator landing authority already supplied by this execution request, then run post-merge documentation reconciliation.
- [ ] Close the claim, verify merged `main`, remove the merged worktree/branch safely, and retain recovery evidence.

## Recovery

Every remote mutation is repeatable from versioned settings and defaults to preview. Local evidence writes preserve the previous valid file until atomic replace succeeds. Git and GitHub history provide branch, PR, issue, and Project recovery; no delete operation is introduced.
