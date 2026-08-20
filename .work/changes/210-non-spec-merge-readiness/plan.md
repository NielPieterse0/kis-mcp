# Non-SPEC Merge Readiness Implementation Plan

**Goal:** Remove the false SPEC-only coupling from merge/documentation traceability without weakening existing gates.

**Architecture:** Add a generic `implementation_record_id` to trace and documentation-event contracts. Keep `specification_record_id` optional and SPEC-only. Parsers fall back from missing generic identity to the legacy specification identity, preserving schema-v1 payload compatibility. Readiness and documentation identity checks use the generic identity.

**Tech Stack:** Python dataclasses, pytest, PowerShell change workflow.

## Global constraints

- Stay inside `scope.json`.
- Add tests before behavior changes and prove the expected red failure.
- Preserve exact-head GitHub Actions verification and documentation policy.
- Do not alter unrelated Work Management lifecycle semantics.

### Task 1: Contract and parser TDD

- Test non-SPEC `BUG-*`/`TASK-*` trace identity and legacy SPEC fallback.
- Test optional SPEC identity remains prefix-restricted.
- Test JSON parsing/serialization carries both identities correctly.

### Task 2: End-to-end lifecycle

- Make merge readiness compare the Work record to `implementation_record_id`.
- Make documentation events inherit and enforce the generic identity.
- Prove non-SPEC merge-ready and documentation reconciliation paths.

### Task 3: Verification and review

- Run focused affected tests and lint/type checks as applicable.
- Run `scripts/change-workflow.ps1 check`.
- Review public contract, tests, and final diff; resolve blocking findings.
