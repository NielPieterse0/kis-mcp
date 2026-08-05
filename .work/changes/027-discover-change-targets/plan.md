# Discover Change Targets Implementation Plan

> **For agentic workers:** Execute task-by-task in this worktree. Use test-driven development, review each task against `spec.md`, and run the locked repository verification before closeout.

**Goal:** Generalize `inspect_change` to bounded local Git targets while preserving deterministic working-tree behavior and the Discover/Work boundary.

**Architecture:** Add immutable target inventory contracts, a fixed-template local Git target reader, and a service layer that normalizes all targets into the existing response shape plus additive target identity and typed verification handoffs. Public registration remains deferred.

**Tech Stack:** Python 3.11, dataclasses, direct `subprocess` argument arrays, JSON Schema draft 2020-12, pytest, PowerShell verification wrappers.

## Global constraints

- No network, shell execution, repository-code execution, mutation, hooks, credential helpers, external diff, or text conversion.
- Preserve schema version 1 and prior working-tree fields.
- Use only paths declared in `scope.json`.
- Serialize all full `verify.ps1` runs because the locked editable Python environment is shared.

### Task 1: Contracts and schema

**Files:** `change_inspection_contracts.py`, request/response schemas, `test_change_schema_contracts.py`.

- [ ] Add failing tests for valid source/field combinations and malformed refs.
- [ ] Add target identity and verification-handoff records.
- [ ] Add strict draft-2020-12 request/response schemas.
- [ ] Run the focused contract/schema tests and commit.

### Task 2: Fixed-template target reader

**Files:** `change_targets.py`, `git_change_reader.py`, `test_change_targets.py`.

- [ ] Add failing parser and command-selection tests for working tree, staged, commit, range, and branch sources.
- [ ] Implement immutable target inventory and deterministic name-status parsing.
- [ ] Implement bounded direct Git templates using the existing metadata validation and isolated environment patterns.
- [ ] Add timeout, truncation, invalid-ref, rename/copy, and Git-failure tests.
- [ ] Run focused target-reader tests and commit.

### Task 3: Service normalization and handoffs

**Files:** `change_service.py`, `test_change_service.py`.

- [ ] Add failing tests for generalized target identity, compatibility, impact counts, unknowns, and verification handoffs.
- [ ] Update the reader protocol and service normalization.
- [ ] Preserve deterministic fingerprints and prior working-tree classifications.
- [ ] Run all affected Discover tests and commit.

### Task 4: Review, verification, and closeout

- [ ] Run `change-workflow.ps1 check`.
- [ ] Run `git diff --check`.
- [ ] Review specification compliance, security boundaries, edge cases, and scope.
- [ ] Run the full locked `scripts/verify.ps1` suite.
- [ ] Complete tasks and closeout, push, open a PR, review, merge, and clean the worktree.
