# Codex Fingerprint Stability Implementation Plan

**Goal:** Fix #261 without weakening the read-only mutation guard.

**Architecture:** Keep the existing fingerprint state dimensions and comparison. Change only native Git capture so successful stdout is serialized as state evidence while stderr diagnostics are excluded; command exit codes remain authoritative for failure.

**Tech stack:** PowerShell 7, Git, pytest, Python 3.11+.

## Global constraints

- Stay inside `scope.json`.
- Add regression coverage before behavior changes.
- Preserve exit code 86 and `CODEX_CLI_MUTATION_DETECTED` for actual mutations.
- Preserve all Codex CLI sandbox/authentication/execution arguments.

### Task 1 — Reproduce and lock the false positive

**Requirements:** R1, R2
**Files:** `tests/tools/codex_cli/test_adapter.py`
**Evidence:** focused pytest must fail against the current wrapper because stderr line-ending diagnostics destabilize the serialized fingerprint.

- [ ] Add a synthetic dirty-diff no-op wrapper test.
- [ ] Confirm the new test fails with exit code 86 before implementation.

### Task 2 — Stabilize Git fingerprint capture

**Requirements:** R1, R2, R4
**Files:** `scripts/invoke-codex-agent.ps1`
**Evidence:** dirty-diff test turns green; existing real-mutation test remains green.

- [ ] Exclude successful Git stderr diagnostics from the hashed state document.
- [ ] Keep existing typed non-zero Git command failures unchanged.
- [ ] Rerun focused Codex adapter/wrapper tests.

### Task 3 — Review and verify

**Requirements:** R1-R4
**Evidence:** scope check, focused tests, required code-quality review, affected verification.

- [ ] Run `pwsh -NoProfile -File scripts/change-workflow.ps1 check`.
- [ ] Run focused Codex tests through the locked external interpreter.
- [ ] Run required code-quality review against this worktree.
- [ ] Re-run affected checks after any review fix.
- [ ] Record closeout evidence and prepare a reviewable commit/PR.

## Recovery

Revert the bounded wrapper/test commit. No state migration or deployment rollback is required.
