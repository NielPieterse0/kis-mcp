# Tasks: Lossless Legacy Transfer Ledger

- [x] Confirm #497 Work authority, repository authority, MCP 2026 corpus, and documentation-only scope.
- [x] Mechanically prove 84 unique superseded source issues + five unique retained Deferred items = 89 mapped sources.
- [x] Expand source issues into normalized material requirement rows and assign one controlled #497 disposition per row.
- [x] Re-baseline MCP-facing rows against the 2026-07-28 specification/schema and record current replacement rationale where legacy prescriptions are obsolete.
- [x] Record #475 current implementation/merge/live evidence and preserve its trigger-defined follow-ups separately.
- [x] Generate deterministic JSON ledger plus concise audit note; validate schema/counts/owner uniqueness with a local checker.
- [x] Run `pwsh -File scripts/change-workflow.ps1 check`, documentation/data checks, `git diff --check`, and canonical `pwsh -File scripts/verify.ps1`.
- [x] Run bounded documentation/API/architecture review attempts; all failed closed on full-ledger evidence size, then complete the required exact-diff deterministic/manual fallback without accepting partial evidence.
- [ ] Commit/publish exact head, require canonical exact-head verification and Work merge-readiness, merge, reconcile #497, and clean the governed change.
