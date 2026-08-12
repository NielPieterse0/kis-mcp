# Executable Change Workflow Implementation Plan

> **For agentic workers:** Execute this plan task-by-task and keep the declared scope current.

**Goal:** Compose existing selection, verification execution, and specialist review contracts into one bounded executable change workflow.

**Architecture:** Add a focused `workflows/change_execution` package containing result contracts, orchestration service, and FastMCP tool registration. Register it from the existing verification platform seam. The service receives one fixed internal invoker and can call only `select_change_verification`, `run_verification`, and `review_change_with_agent`; caller input never chooses a nested operation.

**Tech Stack:** Python 3.11+, FastMCP 3.4.4, pytest, existing KIS Discover/verification/reviewer contracts.

## Global constraints

- Stay inside `scope.json`.
- Add tests before behavior changes.
- Preserve original nested tool schemas and `run_middleware=True`.
- Do not alter policy, reviewer backends, verification discovery, or command construction.

### Task 1 — TDD contract and orchestration behavior

- [ ] Add failing tests for fixed-step execution order, aggregation, failure retention, bounded review purposes, and narrow public schema.
- [ ] Confirm the new tests fail because the package/tool does not exist.
- [ ] Implement immutable execution result contracts and validation.
- [ ] Implement the orchestration service with fixed nested operation names only.
### Task 2 — Platform registration

- [ ] Register `execute_change_workflow` beside selector/runner construction in `verification/platform.py`.
- [ ] Convert nested FastMCP results to bounded structured payloads; reject invalid nested result shapes structurally.
- [ ] Update gateway registration regression coverage without changing the direct-profile configuration.

### Task 3 — Review and verification

- [ ] Run focused change-execution, verification, and registration tests.
- [ ] Run `pwsh -File scripts/change-workflow.ps1 check` and `git diff --check`.
- [ ] Run specialist review attempts against the final diff and record backend failures accurately.
- [ ] Run canonical `pwsh -File scripts/verify.ps1` on the exact final state.
- [ ] Reconcile change artifacts, commit, publish exact head, merge PR, and clean the governed worktree.

## Recovery

Revert the slice commit/merge. No migration, generated state, provider installation, or policy rollback is required.
