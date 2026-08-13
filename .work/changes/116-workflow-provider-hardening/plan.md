# Workflow Provider Hardening Implementation Plan

> **For agentic workers:** Execute inline in this isolated worktree. Use test-first changes, focused review checkpoints, and one canonical full verification on the exact PR head.

**Goal:** Remove the concrete workflow/provider defects captured in `SPEC-116` while preserving KIS exact-change safety and the operator Work Management hold.

**Architecture:** Fix each defect at its owning boundary rather than adding coordinator ceremony: target-reader wiring in verification platform composition; source-path isolation in verification execution; tree-equivalent exact-tree publication plus explicit-base three-way reconciliation for diverged registered GitHub review branches; idempotent/generated-state handling inside provider adapters. Existing contracts are preserved unless the requirement explicitly changes internal behavior.

**Tech Stack:** Python 3.12/3.13, FastMCP 3.4.4, pytest, PowerShell verifier, Git, KIS registered GitHub operations.

## Global constraints

- Stay inside `scope.json`; update claims before edits.
- No writes outside `C:\Projects`, no ordinary Work network, no permanent delete.
- Tests must fail for the intended reason before production edits.
- Preserve exact remote-default SHA checks, exact branch leases, default-branch publication blocks, and exact published-tree checks.
- Do not duplicate the canonical full verifier; focused tests are allowed before PR publication.
- Keep Work Management `SPEC-116` open / not `Done` after merge until operator verification.

---

### Task 1: Repair exact-commit verification selection

**Files:**
- Modify: `src/kis_mcp/workflows/verification/platform.py`
- Test: `tests/workflows/verification/test_verification_platform.py`

- [ ] Add a regression proving platform composition uses a target-capable Git reader for `source=commit`.
- [ ] Run the focused test and confirm the current platform wiring fails the regression.
- [ ] Replace local-only `GitReader` composition with `GitChangeReader` without changing public selection contracts.
- [ ] Run focused verification and confirm the known clean-commit reproduction returns commit-derived evidence.

### Task 2: Isolate verification imports and review defaults

**Files:**
- Modify: `src/kis_mcp/workflows/verification/execution.py`
- Test: `tests/workflows/verification/test_verification_execution.py`
- Test: `tests/workflows/change_execution/test_change_execution_service.py`

- [ ] Add a failing command-construction test requiring `<project>/src` first on child `PYTHONPATH` when present.
- [ ] Implement process-local source-path prepending without mutating the parent environment.
- [ ] Add/confirm regression coverage that explicit empty `review_types` performs no review while omitted reviews retain risk defaults.
- [ ] Run focused verification.

### Task 3: Reconcile verified changes safely over divergent remote bases

**Files:**
- Modify: `src/kis_mcp/projects/github_exact.py`
- Test: `tests/workflows/test_registered_commit_publication.py`
- Test: `tests/workflows/completion/test_completion_service.py`

- [x] Add failing publication regressions for a source-base tree that differs from verified remote default and for a conflicting three-way merge.
- [x] Keep the exact source-tree fast path only when source-base and remote-default trees are equivalent.
- [x] For divergence, use `git merge-tree --write-tree --merge-base <source-base> <remote-default> <source>`; publish the resulting tree on the exact remote-default parent and fail closed on merge conflict.
- [x] Retain source-base ancestry, remote SHA, exact branch lease, default-branch, and post-publish checks; return bounded base-relation/publication semantics.
- [x] Prove the actual 115/116 concurrency case: the explicit-base merge tree equals the rebased 116 implementation tree, preserving independently landed 115 content.

### Task 4: Make DBHub generated config idempotent

**Files:**
- Modify: `src/kis_mcp/providers/dbhub/adapter.py`
- Test: `tests/providers/test_dbhub_dockerhub_integration.py`

- [ ] Add a failing regression proving a second identical render does not rewrite `dbhub.toml`.
- [ ] Implement compare-before-write inside generated runtime state.
- [ ] Run focused DBHub tests.

### Task 5: Harden Serena project activation and Windows output

**Files:**
- Modify: `src/kis_mcp/providers/serena/adapter.py`
- Test: `tests/providers/test_context7_serena_providers.py`

- [ ] Add failing tests for UTF-8 child environment and conservative repair of exact empty `languages: []` state from bounded source suffixes.
- [ ] Implement UTF-8 environment flags and central generated-state repair; never overwrite non-empty languages.
- [ ] Run focused Serena tests and a live semantic smoke on a registered Python project if the runtime remains available.

### Task 6: Remove deprecated DockerHub transformation API

**Files:**
- Modify: `src/kis_mcp/providers/dockerhub/adapter.py`
- Test: `tests/providers/test_dbhub_dockerhub_integration.py`

- [ ] Add a failing source/behavior regression requiring current `Visibility` transforms and fail-closed public exposure.
- [ ] Replace `add_tool_transformation`/`ToolTransformConfig` with hide-all then allow-approved `Visibility` transforms.
- [ ] Run focused provider tests.

### Task 7: Integrate, review, land, and preserve operator hold

**Files:**
- Update: `.work/changes/116-workflow-provider-hardening/tasks.md`
- Update: `.work/changes/116-workflow-provider-hardening/closeout.md`

- [ ] Run the relevant focused test files together and `scripts/change-workflow.ps1 check 116-workflow-provider-hardening`.
- [ ] Review the current diff for correctness, unnecessary complexity, and safety regressions; fix validated findings only.
- [ ] Commit the exact implementation state and use the reviewable-PR coordinator where functional; use its preserved exact primitives only for a demonstrated coordinator defect.
- [ ] Run `scripts/verify.ps1` once on the exact GitHub PR head and record that single canonical result.
- [ ] Merge only the exact verified head with the repository’s required merge strategy; verify remote `main`; clean only verified feature refs/worktree state allowed by policy.
- [ ] Leave GitHub issue #156 open and Work Management `SPEC-116` not `Done`, explicitly marked awaiting operator verification.

## Self-review

- Requirements REQ-001..REQ-009 are mapped to Tasks 1-7 or explicit out-of-scope boundaries.
- No task changes the three hard policy rules, credentials, generated secrets, or production state.
- No placeholders remain; broader `project`/`path` public aliasing is intentionally excluded because it is a public-contract design change, while current coordinator translation remains regression-covered.
