# Merge Queue Canonical State Implementation Plan

**Goal:** Route merge-queue durable state through the canonical project-specific KIS namespace and preserve bounded legacy recovery.

**Architecture:** Keep `MergeQueueSettings.state_root` as the legacy compatibility location. Production `QueueStateStore` resolves canonical paths using `StateNamespaceResolver`; tests can inject a bounded path resolver. Canonical state is preferred, legacy state is fallback-only, and the next mutation writes canonical state atomically.

**Tech Stack:** Python, pytest, KIS state ownership contract, existing merge-queue store/locking.

## Global constraints
- Stay inside `scope.json`.
- Do not create a second state identity model.
- Do not delete legacy state.
- Preserve queue locking, exact-head semantics, and GitHub/repository authority.

### Task 1 — Canonical path ownership
- [x] Add project-specific namespace resolution for production queue state.
- [x] Derive collision-resistant branch-specific state keys.

### Task 2 — Compatibility recovery
- [x] Read validated legacy state only when canonical state is absent.
- [x] Preserve legacy evidence and prefer canonical state after migration.

### Task 3 — Verification
- [x] Add regression coverage for legacy-to-canonical preference.
- [x] Run focused queue + state-contract suites and `git diff --check`.
- [ ] Complete specialist review, commit, exact-head CI, merge, commissioning, and Work closeout.