# Disposable Windows Execution Foundation Implementation Plan

> Execute task-by-task; keep `scope.json` authoritative and stop before canonical CI migration.

**Goal:** Establish the execution-backend abstraction and one disposable Windows Hyper-V proof path while preserving current verification and merge authority.

**Architecture:** `VerificationExecutionService` delegates execution to a provider-neutral backend/profile contract. `local-process` remains the compatibility backend. A new Hyper-V backend owns guest lifecycle and returns the same bounded verification semantics plus runner/image provenance. GitHub Actions integration remains a later consumer of this substrate.

**Tech stack:** Python 3.13, existing KIS verification contracts, PowerShell 7, Windows Hyper-V, JSON settings/contracts, existing KIS evidence and Work middleware patterns.

## Global constraints

- Stay inside `scope.json`; `.github/workflows/**` remains excluded. `SPEC.md` is included only for bounded current-product reconciliation.
- Add failing tests before behavior changes.
- Do not mount host KIS state, secrets, or the mutable development checkout into the guest.
- Do not add a Work-policy decision beyond HR-001/HR-002/HR-003.
- Keep GitHub control/landing authority unchanged.

### Task 0 — roadmap and target-architecture placement

**Files:** `.work/changes/174-disposable-windows-execution-foundation/**`, `docs/PLATFORM-CONCEPT.md`

- [x] Capture the complete multi-slice sequence in `roadmap.md` and issue `#324`.
- [x] Add only the durable execution-substrate target boundary to `docs/PLATFORM-CONCEPT.md`.
- [x] Keep current implementation claims and phase status out of the target-state document.
- [x] Record first-slice exclusions so canonical CI and `import-isolate` are not changed prematurely.

### Task 1 — execution contracts and settings

**Files:** `src/kis_mcp/execution/**`, `contracts/execution/**`, `settings/execution-runners.settings.json`, `tests/execution/**`

- [x] Define backend/profile/readiness/request/result/lifecycle identities and strict JSON settings.
- [x] Add validation for exact source/image/profile identity, KIS-owned host state, and bounded evidence.
- [x] Cover malformed settings, unsupported profiles, stale identity, repeated attempts, and incomplete lifecycle outcomes.

### Task 2 — verification adapter

**Files:** `src/kis_mcp/workflows/verification/**`, `tests/workflows/verification/**`

- [x] Route current local-process execution through the new backend contract with no externally observable regression.
- [x] Preserve verification declaration, command identity, status/failure classification, and evidence bounds.
- [x] Add tests proving backend selection cannot authorize otherwise unavailable Work effects.

### Task 3 — Hyper-V proof backend

**Files:** `src/kis_mcp/execution/**`, `scripts/runner/**`, `tests/execution/**`

- [x] Add readiness checks for required Hyper-V host capabilities.
- [x] Implement fresh-attempt guest create/start/inject/execute/collect plus HR-003-compatible retire/quarantine lifecycle with bounded timeouts.
- [x] Bind the guest to exact source/image/profile identities before execution.
- [x] Prove host checkout, KIS state, user profile, and credentials are not guest inputs by default.
- [x] Return bounded diagnostics and explicit incomplete/failure receipts for every lifecycle failure class.

### Task 4 — proof, review, and handoff

- [x] Execute one existing declared verification through `local-process` and the disposable Windows contract path and compare contract-level results in the deterministic proof harness.
- [x] Move live Hyper-V startup/setup/verification/transfer measurements and supervised commissioning to follow-up issue `#330`; unavailable host capability no longer blocks landing this implementation foundation.
- [x] Run architecture and safety/security review gates; use the exact-diff manual fallback when specialist backends fail, and resolve all blocking findings.
- [x] Run focused tests, `scripts/change-workflow.ps1 check`, `git diff --check`, and applicable local repository verification.
- [x] Record the current Hyper-V host limitation without claiming canonical CI parity.
- [x] Leave GitHub runner, scale-set, canonical workflow, and `import-isolate` follow-ups to `roadmap.md`.
