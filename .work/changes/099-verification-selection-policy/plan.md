# Verification Selection Policy Implementation Plan

> Execute in the isolated 099 worktree with tests before behavior changes.

**Goal:** Add deterministic read-only selection between Discover impact handoffs and existing Work verification execution.

**Architecture:** Extend the existing verification workflow module. Analyze the requested change, re-inspect current project declarations, reconcile exact handoff identity, classify non-runnable evidence, then return a bounded non-executable selection contract. Do not introduce a scanner, command parser, generic policy engine, or executor.

**Tech Stack:** Python stdlib, existing Discover contracts/services, FastMCP, pytest.

## Global constraints

- Stay inside `scope.json` and do not touch active 098-owned paths.
- Preserve existing `run_verification` execution semantics.
- Selection must remain read-only and local.
- No new dependency, provider, network path, or HR decision.

### Task 1 — Selection contract and service

- [x] Add failing tests for ordering, stale evidence, unsupported profiles, and limits.
- [x] Implement typed selection items/issues/result and deterministic reconciliation.
- [x] Keep every selected item `execution_available=false`.

### Task 2 — Public read-only handoff

- [x] Add `select_change_verification` with no command argument.
- [x] Wire it through the existing platform verification registration.
- [x] Update gateway registration regression coverage.

### Task 3 — Verification and delivery

- [x] Run focused verification workflow and gateway registration tests.
- [ ] Run scope, whitespace, canonical repository verification, and bounded review.
- [ ] Commit, publish, PR, exact-head merge, close record, and governed cleanup.
