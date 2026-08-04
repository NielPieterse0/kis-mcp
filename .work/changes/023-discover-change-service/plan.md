# Discover Working-Tree Change Service Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Add a deterministic internal `inspect_change` working-tree service over the merged local Git change inventory.

**Architecture:** Define immutable request/response records in a new contract module. Inject the existing local-change reader into a pure projection service that performs deterministic classification, scope derivation, fingerprinting, confidence, and unknown-state construction without subprocess, network, public registration, or settings changes.

**Tech Stack:** Python 3.11+, dataclasses, enum, hashlib, json, pathlib-style path normalization, pytest, jsonschema.

## Global Constraints

- Write only within `C:\Projects`.
- Discover remains read-only and must not execute repository code or use the network.
- Work policy remains exactly HR-001, HR-002, and HR-003.
- Existing Discover files are dependencies only and are not modified in this slice.
- Public `inspect_change` registration, arbitrary refs, caller-controlled commands, and remote evidence are excluded.

---

### Task 1: Request and response contracts

**Files:**
- Create: `src/kis_mcp/discover/change_inspection_contracts.py`
- Create: `contracts/discover/inspect-change-working-tree-response.schema.json`
- Test: `tests/discover/test_change_service.py`

**Interfaces:**
- Produces: `InspectChangeRequest`, `ChangedFile`, `ChangeIdentity`, `ChangeImpactSummary`, `ChangeUnknown`, and `InspectChangeResponse`.
- Fixed identities: schema version `1`, tool `inspect_change`, source `working_tree`.

- [x] **Step 1: Write failing tests for request validation and exact response serialization.**
- [x] **Step 2: Run the focused test file and confirm import failure because the contract module is absent.**
- [x] **Step 3: Implement frozen slotted dataclasses, enums, validation, and explicit JSON serialization.**
- [x] **Step 4: Add the strict Draft 2020-12 response schema and validate a representative payload.**
- [x] **Step 5: Run focused contract tests and confirm they pass.**

### Task 2: Pure working-tree projection service

**Files:**
- Create: `src/kis_mcp/discover/change_service.py`
- Test: `tests/discover/test_change_service.py`

**Interfaces:**
- Consumes: a reader with `inspect_local_changes(project_path: str) -> LocalChangeInventory`.
- Produces: `InspectChangeService.inspect(request: InspectChangeRequest) -> InspectChangeResponse`.

- [x] **Step 1: Add failing tests for retained change fields, path classification, affected scopes, deterministic fingerprinting, confidence, diagnostics, and unknowns.**
- [x] **Step 2: Run focused tests and confirm failures because the service is absent.**
- [x] **Step 3: Implement the minimal pure projection with no filesystem, subprocess, network, settings, or public-tool side effects.**
- [x] **Step 4: Run focused tests and confirm the service cases pass.**
- [x] **Step 5: Refactor only after green to keep classification tables and ordering explicit and small.**

### Task 3: Real reader composition and verification

**Files:**
- Modify: `tests/discover/test_change_service.py`
- Modify: `.work/changes/023-discover-change-service/tasks.md`
- Modify: `.work/changes/023-discover-change-service/closeout.md`

**Interfaces:**
- Consumes: `GitReader.inspect_local_changes()` and `InspectChangeService`.
- Produces: current integration, architecture, scope, and verification evidence.

- [x] **Step 1: Add a real temporary-repository test proving staged, unstaged, and untracked changes flow through the service.**
- [x] **Step 2: Run focused and affected Discover tests with `PYTHONPATH` bound to this worktree and `--no-sync`.**
- [x] **Step 3: Confirm no new `subprocess` import exists outside `git_reader.py` and no public registration files changed.**
- [x] **Step 4: Run `change-workflow.ps1 check`, `git diff --check`, then serialized full `verify.ps1` when the shared environment is free.**
- [x] **Step 5: Review requirements R1-R11 against the final diff and fresh evidence, update closeout, commit, push, and open a small PR.**
