# Change: Exact Target Work Resolution

- **Change ID**: `173-exact-target-work-resolution`
- **Risk Profile**: lean

## Outcome

Make exact-target Work Management mutations resolve known repository issues beyond the default bounded Project inventory while preserving fail-closed ambiguity and revision-safe reconciliation.

## Scope and acceptance

- Implement only the paths declared in `scope.json`.
- Exact-target Work Management commands must resolve a known repository/issue beyond the default 100-item Project inventory bound through a finite bounded scan.
- If the bounded scan remains incomplete, exact-target resolution must fail closed even when one matching item was observed, because an unseen duplicate cannot be excluded; duplicate exact matches must still fail as ambiguous.
- `claim_work`, `release_work`, `transition_work`, `sync_change_classification`, and `complete_work` must share the corrected resolver without weakening lifecycle, revision, reconciliation, or idempotency gates.
- Broad queue selection (`next_work`) must retain its existing 100-item fail-closed truncation behavior.

## Implementation and verification

- Implementation notes: test-first regressions proved the 100-item failure; `_issue_command_inventory` now uses a finite 1,000-item exact-target scan, surfaces already-observed duplicate matches, and refuses to accept zero/one-match resolution while the scan remains truncated. `claim_work`, `release_work`, `transition_work`, `sync_change_classification`, and `complete_work` all use that shared resolver; `next_work` remains bounded at 100.
- Focused checks: `test_command_service.py` 16/16 passed; affected `test_command_service.py` + `test_project_commands.py` + `test_service.py` 29/29 passed; Ruff passed; `scripts/change-workflow.ps1 check` passed with only declared paths.
- Review findings: the first KIS Codex review passed; the final-state review then caught a medium ordering defect where two already-visible duplicates could be masked by truncation. A new regression reproduced it, and resolution now reports observed duplicates before failing incomplete for zero/one visible match on a still-truncated scan. Direct source inspection confirms all five exact-target commands use the shared resolver.
- Verification limitation: broader Work Management/workflow collection is blocked by the existing `kis_mcp.workflows.project_management` circular-import failure; `tests/work_management/test_cli.py` reproduces identically on clean `main`, and that defect is already in the separate active #271 lane.
- Residual risk: a Project larger than the finite exact-target scan remains an explicit `inventory_incomplete` result rather than a false not-found or potentially ambiguous mutation.
- Closeout state: implementation and affected local verification complete; exact-head pull-request CI remains the publication/landing gate.
