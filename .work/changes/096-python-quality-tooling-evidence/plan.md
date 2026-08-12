# Python Quality Tooling Evidence Implementation Plan

> Execute task-by-task in the isolated 096 worktree; tests precede behavior changes.

**Goal:** Add deterministic Discover evidence for declared Python quality tooling without installing or executing project tools.

**Architecture:** Extend the existing `VerificationDiscoveryService` rather than adding a competing scanner or workflow engine. Parse `pyproject.toml` structurally with stdlib `tomllib`, normalize recognized Python tooling into additive evidence records, and reuse existing `VerificationDeclaration` handoffs only for stable command contracts. Keep LibCST as capability evidence only. Actual tool availability, selection, execution, and enforcement remain later Work responsibilities.

**Tech Stack:** Python 3.11–3.13 stdlib (`tomllib`, regex/dataclasses), existing Discover contracts, pytest.

## Global constraints

- Stay inside `scope.json`; do not touch active 095-owned paths.
- Do not add or install dependencies.
- Do not execute repository-discovered commands or quality tools.
- Preserve existing declaration IDs/ordering and current Discover/Work authority boundaries.
- Add tests before behavior changes.

### Task 1 — Quality-tool evidence contract

**Files:** `src/kis_mcp/discover/verification.py`, `tests/discover/test_verification_discovery.py`.

- [ ] Add failing tests for normalized Ruff, coverage.py/pytest-cov, Vulture, LibCST, mypy, and pyright evidence.
- [ ] Add deterministic `QualityToolEvidence` records to verification-discovery output.
- [ ] Parse dependencies/config structurally and distinguish dependency-backed vs config-only evidence.

### Task 2 — Stable non-executing handoffs

**Files:** same.

- [ ] Add failing tests for exact Ruff/coverage/Vulture/type-checker declaration IDs, profiles, and arguments.
- [ ] Reuse `VerificationDeclaration` with `authority=discovered_only` and `execution_available=false`.
- [ ] Keep LibCST evidence non-executable with no verification ID.

### Task 3 — Malformed-input and compatibility gate

**Files:** same.

- [ ] Add malformed-TOML regression proving unrelated workflow discovery continues.
- [ ] Run the complete verification-discovery test module and affected Discover regressions.
- [ ] Run `scripts/change-workflow.ps1 check`, `git diff --check`, and canonical `scripts/verify.ps1`.
- [ ] Run independent review unless the operator separately waives it for this slice.
- [ ] Commit, publish, PR, merge exact approved head, close status, and clean only 096.
