# Repo Local Recovery Capsule Implementation Plan

> **For agentic workers:** Execute task-by-task; repository authority and `scope.json` remain binding.

**Goal:** Add a validated, reconstructible `.temp\kis` recovery capsule to each registered project and use it as a non-authoritative hint/checkpoint layer.

**Architecture:** Add `ProjectRecoveryCapsule` in the project domain. It derives the capsule root from `ProjectDefinition.local_root`, isolates current pointers by a hash of the active worktree, and delegates atomic immutable generations to the shared `EvidenceStore`. Discover publishes a typed hint after central persistence succeeds. Operation checkpoints use the same generation stream and fixed fields; they cannot carry authorization or secrets.

**Tech Stack:** Python 3, dataclasses, pathlib, SHA-256/JSON, existing `EvidenceStore`, pytest, PowerShell repository verification.

## Global constraints

- Stay inside `scope.json`; do not touch `AGENTS.md` while change 125 owns it.
- Add tests before behavior changes.
- No arbitrary metadata, credentials, provider authorization, or network semantics in capsule payloads.
- Central `C:\Projects\.kis-mcp` evidence remains authoritative; local state is disposable.

### Task 1: Specify recovery semantics

**Files:** `.work/changes/136-repo-local-recovery-capsule/{spec.md,plan.md,tasks.md}`

- [x] Define authority, fingerprints, concurrency, corruption, idempotency, and recovery behavior.
- [x] Record the active 125 `AGENTS.md` ownership boundary and avoid overlap.

### Task 2: Add failing capsule unit tests

**Files:** `tests/projects/test_recovery.py`

- [ ] Test registered-root placement, current/stale validation, corrupt-pointer recovery, worktree separation, and operation checkpoint idempotency/conflicts.
- [ ] Run focused tests and confirm expected failure before implementation.

### Task 3: Implement the recovery capsule kernel

**Files:** `src/kis_mcp/projects/recovery.py`, `src/kis_mcp/projects/__init__.py`

- [ ] Implement typed recovery identity and status/result contracts.
- [ ] Derive `<registered-root>\.temp\kis` and worktree-specific namespaces deterministically.
- [ ] Reuse `EvidenceStore` for immutable atomic generations and corrupt-pointer retention.
- [ ] Implement bounded started/completed operation checkpoints and conflicting idempotency-key detection.
- [ ] Keep payloads fixed-schema and secret-free.

### Task 4: Integrate Discover as the first production consumer

**Files:** `src/kis_mcp/discover/intelligence.py`, `tests/discover/test_intelligence.py`

- [ ] Publish a local recovery hint only after central Discover generation publication succeeds.
- [ ] On central-generation reuse, refresh/validate the hint without allowing it to decide authority.
- [ ] Expose bounded capsule status in the existing persistence result for diagnostics.
- [ ] Verify absence/staleness/corruption never blocks central correctness.

### Task 5: Reconcile architecture and operations documentation

**Files:** `SPEC.md`, `docs/OPERATIONS.md`

- [ ] Define the capsule as a non-authoritative recovery projection under each registered repo `.temp\kis`.
- [ ] Document invalidation, cleanup, corruption handling, and worktree concurrency semantics.
- [ ] Keep central state and external/provider authority unchanged.

### Task 6: Review, verify, and land

- [ ] Run focused pytest suites.
- [ ] Run `pwsh -File scripts/change-workflow.ps1 check` and required repository verification.
- [ ] Run architecture/security/code-quality review against exact diff and fix blockers.
- [ ] Commit and prepare a reviewable PR through KIS.
- [ ] Require exact-head GitHub Actions success, then land through the governed queue/merge workflow.
- [ ] Refresh registered default branch, reconcile documentation and Work Management, close issue #207, and safely clean the worktree.
