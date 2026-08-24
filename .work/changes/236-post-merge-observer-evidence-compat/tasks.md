# Tasks: Post-Merge Observer Evidence Compatibility

## Design gate

- [x] Re-read `AGENTS.md`, Change 228 authority, current `SPEC.md`, settings, live observer evidence, and Work #474.
- [x] Confirm Change 236 scope and parallel Change 232 ownership conflict on `SPEC.md`.
- [x] Classify as Complex / `large` with architecture, external-action, persistent-state, and public-contract risk triggers.
- [x] Write requirement-traceable specification R1-R12.
- [x] Write implementation plan T1-T5 with tests, review, recovery, landing, and live acceptance.
- [x] Run exact planning-diff review: architecture clean; API-contract reviewer evidence projector omitted unchanged implementation source, so its implementation-absence findings were resolved by direct source inspection and recorded as non-blocking planning-review limitations.
- [x] Obtain explicit human approval of the finalized specification and plan (`go`, 2026-08-23).
- [x] Reopen after exact-diff safety finding, amend R4/R6-R8, and obtain explicit approval of the safety-review amendment (`go`, 2026-08-23).
- [x] Reopen after provenance review, add PR-head + source Work `Change ID` corroboration, and obtain explicit approval to continue (`go`, 2026-08-24).
- [x] Reopen after live acceptance exposed a 1-second provider/Git timestamp drift on PR #434; replace exact-second equality with a sub-minute sanity bound and obtain explicit approval (`yes timestamp should only show real obvious mismatch`, 2026-08-24).

## Implementation gate

- [x] T1: exact complete merge-file and blob-proven landed-scope source identity, corroborated by exact governed PR head ref and source Work `Change ID`; PR-body text is non-authoritative.
- [x] T2: bounded `blocked_evidence` only for proven immutable landed-governance errors; retryable evidence errors re-raise.
- [x] T3: checkpoint accounted-vs-retryable regression coverage, including changed-file, scope-content, and source Work corroboration uncertainty.
- [x] T4: reconcile operator documentation; after safely retiring Change 232's orphan claim, add the minimal current-product `SPEC.md` reconciliation to Change 236.

## Delivery gate

- [x] Final post-provenance focused/full commissioning tests, Ruff, diff hygiene, and governed scope check pass.
- [x] Final specialist reviews pass with blocking findings resolved; architecture/documentation automated reviews are clean after corrections, and code/API/test/safety used the required complete exact-diff manual fallbacks after bounded evidence projection omitted files.
- [x] Safely retire unimplemented Change 232 ownership and reconcile the minimal current-product `SPEC.md` authority into Change 236.
- [x] First publication passed exact-head canonical Actions and Work merge-readiness; PR #481 merged at `6dd3e74e21678cbd9751081e86d9acf56304da25` and `kis-dev` auto-refreshed to the landed revision.
- [x] First supervised `kis-op` live acceptance reproduced the remaining 1-second timestamp false negative on PR #434; implement the approved sub-minute sanity bound with boundary regressions.
- [ ] Publish the timing-amended follow-up and pass exact-head canonical GitHub Actions plus Work merge-readiness.
- [ ] Merge the approved follow-up head and reconcile canonical documentation ownership.
- [ ] Supervised `kis-op` refresh and live observer acceptance pass on the timing-amended landed runtime.
- [ ] Complete Work #474 and clean Change 236 from synced `main`.