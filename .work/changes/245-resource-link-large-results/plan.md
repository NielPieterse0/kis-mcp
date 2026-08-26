# Resource Link Large Results Implementation Plan

**Goal:** Preserve exact oversized dispatcher evidence through bounded MCP resources without weakening existing execution gates.

**Architecture:** Keep result budgeting in the capability dispatcher. Persist only oversized structured results beneath the generated KIS state root behind opaque random per-dispatch grants, record the originating operation and an independent payload SHA-256, register one read-only `kis-result:///` resource template, and return the existing bounded summary plus a `ResourceLink` when persistence succeeds. Store publication/read/maintenance are synchronized, and expired active entries are moved through the existing recoverable quarantine service rather than permanently deleted.

**Tech stack:** Python 3.13, FastMCP 4, MCP ResourceLink, pytest, JSON settings/schema.

## Constraints

- Stay inside `scope.json`.
- Preserve `RESULT_BUDGET_EXCEEDED` compatibility and small-result behavior.
- No replay of provider/tool operations during resource reads.
- Generated result state is bounded and non-authoritative.

### Task 1: Contract and settings
- Extend result-budget settings/schema with TTL, entry-count, and byte bounds.
- Add settings validation coverage.

### Task 2: Result resource store
- Add opaque per-dispatch grant persistence, payload integrity verification, synchronized reads/maintenance, recoverable expiry quarantine, and read-only resource registration.

### Task 3: Dispatcher integration
- Attach the store only in production composition.
- Return summary + ResourceLink for oversized results; preserve existing fallback if storage is unavailable or too large.

### Task 4: Verification and documentation
- Prove exact resource retrieval and unchanged small-result behavior.
- Update `SPEC.md`, run focused checks, governance, specialist reviews, and publication workflow.
