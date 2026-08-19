# Tasks: Housekeeping Source Inventory

- [x] Confirm Change 194/199/202 authority, live scheduler state, and exact source-evidence failure.
- [x] Prove `github_list_issues` can return a cursor-complete live open-issue inventory.
- [x] Preserve legacy issue/status/metadata semantics as an explicit non-goal.
- [x] Add failing regressions for historical-source read exhaustion and repeated dependency reads.
- [x] Implement complete open-issue inventory acquisition with exact-read fallback.
- [x] Implement successful per-run exact dependency-state caching.
- [x] Run focused housekeeping tests, Ruff, diff check, and `scripts/change-workflow.ps1 check`.
- [x] Run required specialist reviews on the full base→candidate range and reconcile findings.
- [ ] Freeze final head, publish PR, and obtain canonical exact-head GitHub Actions success.
- [ ] Merge exact head and refresh/restart `kis-op` on merged revision.
- [ ] Obtain fresh unattended `complete=true` receipts from both housekeeping runners.
- [ ] Reconcile Hold #379 and Change 194 / #364 only after live proof is green.
- [ ] Preserve Change 195 untouched until Change 194 closeout completes.