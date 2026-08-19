# Change: Housekeeping Evidence Read Bound

- **Change ID**: `202-housekeeping-evidence-read-bound`
- **Risk Profile**: lean

## Outcome

Raise the bounded unattended housekeeping source-evidence read budget above the live repository requirement so both scheduled previews can complete while preserving fail-closed evidence semantics.

## Scope and acceptance

- Implement only the paths declared in `scope.json`.
- Preserve the existing runner algorithms, preview-only scheduler policy, and fail-closed behavior when source evidence remains incomplete.
- Raise both checked-in production `max_external_reads` bounds from `100` to `200`; the runtime parser's existing hard maximum of `1000` remains unchanged.
- The new production bound must exceed the live 2026-08-19 unattended requirement: both runners exhausted `100` reads with exactly `3` source failures remaining.
- Completion still requires fresh unattended `complete=true` receipts from both runners after this configuration lands.

## Implementation and verification

- Root-cause evidence: Change 201 removed false transport/inventory truncation. Natural scheduled receipts at `10:51:07Z` and `10:51:37Z` scanned 135 live records and failed only with `source_evidence_incomplete`; each reported `max_external_reads=100` and `source_failures=3`.
- TDD evidence: the checked-in configuration regression failed with `{100} != {200}` before the settings change.
- Implementation notes: only the two canonical production evidence-read bounds were raised to `200`; no runner, scheduler, apply, or provider logic changed.
- Focused checks: canonical settings suite 12/12 passed; combined `tests/housekeeping_runtime tests/housekeeping` completed exit 0 with 64 tests; Ruff clean; `git diff --check` clean; `scripts/change-workflow.ps1 check` reported only the four declared paths.
- Review findings: working-tree fingerprint `2209038151ae01824a199b7f84f10cd71248305a288ec805440f226007978197`; code-quality, architecture, and test-quality specialist reviews completed clean with no findings. The test-quality backend timed out once and completed clean on its automatic retry.
- Residual risk: repository growth can again exhaust the finite `200`-read bound; that remains an intentional fail-closed signal rather than an unbounded external-read path.
- Closeout state: local verification, specialist review, exact-head Actions, merge, runtime restart, and fresh natural scheduled success receipts remain required.
