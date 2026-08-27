# Runtime Receipt Canonical Identity Implementation Plan

**Goal:** Namespace runtime receipts and checkpoints by canonical runtime identity while retaining legacy state as recovery-only evidence.

**Architecture:** Reuse `StateNamespaceResolver` and the `runtime-instance-specific` ownership class. Materialize its canonical relative namespace under the configured runtime state root. Keep consumer state formats and lifecycle semantics unchanged.

**Tech Stack:** Python 3.13, FastMCP 4, PowerShell, pytest, Ruff, governed KIS change workflow.

## Global constraints
- Stay inside `scope.json`.
- Preserve existing state formats and atomic write/lock semantics.
- Never auto-trust identity-ambiguous legacy roots.
- Do not modify reusable authentication or Slice D provider/project evidence.

### Task 1: Canonical runtime namespace helper
- [x] Add a bounded helper backed by `StateNamespaceResolver`.
- [x] Prove separate `kis-op` and `kis-dev` paths.

### Task 2: Runtime consumer migration
- [x] Route commissioning state through normalized runtime identity.
- [x] Route housekeeping state through normalized runtime identity.
- [x] Route post-land restart state to canonical `kis-dev` ownership.

### Task 3: Compatibility and regression
- [x] Retain legacy roots without selecting them as current state.
- [x] Preserve restart ownership, retry/idempotency, freshness, and fallback behavior.
- [x] Run focused cross-runtime and legacy-retention tests.

### Task 4: Governed closeout
- [x] Pass `scripts/change-workflow.ps1 check`.
- [x] Resolve specialist review findings.
- [ ] Publish exact commit and pass exact-head GitHub Actions.
- [ ] Merge, commission current revision, complete #555, and clean Change 254.
