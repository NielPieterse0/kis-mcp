# Closeout: Work Management Commissioning

## Implemented scope

- Bound work management to `NielPieterse0` user Project `#1` and enabled platform composition.
- Preserved all automation flags as `false` and retained reconciliation/review-import as `read_only`.
- Normalized the pinned GitHub MCP live Project read shape: stable `node_id` preference, numeric REST ID fallback, and structured single-select option names.
- Enforced read-only reconciliation before remote apply and read-only review import before local evidence-store writes.
- Did not change GitHub OAuth/provider routing, provider version, policy, or Project remote state.

## Live pre-bind commissioning evidence

- `kis-op` health: ready.
- GitHub MCP: mounted and authenticated for the current runtime; live verification ready.
- User Project `#1`: private `KIS Work Management`, readable through `github_projects_get`.
- Project fields: complete page; `Status` options are `Todo`, `In Progress`, and `Done`.
- Project items: zero items; pagination complete.
- No `projects_write` operation was invoked.

## Post-merge commissioning evidence

- PR #80 merged after exact-head Work Management run #17 succeeded on `0c58e9c3c978256ec3abed72816e8674c44ff546`.
- GitHub merge commit: `94ebc6a9bf9e9090a5e218ff560593e24695b1fa`.
- Local `main` was fast-forwarded to the merge commit.
- Authenticated post-merge provider reads confirm user Project `#1` remains private `KIS Work Management` with stable node ID `PVT_kwHODUU4HM4Bfo87`.
- Project fields remain complete; `Status` options are `Todo`, `In Progress`, and `Done`.
- Project items remain empty with pagination complete; no Project write operation was invoked.
- The currently running `kis-op` process predates the merged settings and therefore reports `UNKNOWN_CAPABILITY_OPERATION: project_management_inventory`, which is expected until restart.
- No safe in-process reload is exposed. Startup requires operator vault unlock before the new runtime can mount the composed tool, so final composed inventory and change cleanup remain intentionally pending rather than being falsely declared complete.

## Validation evidence

- Baseline focused tests before edits: 17 passed.
- TDD red: live-shaped field option object failed existing normalization as expected.
- TDD red: stable Project node identity assertion exposed numeric-ID preference as expected.
- TDD green: GitHub Project adapter test file passed (7 tests).
- TDD red: read-only reconciliation still applied and read-only review import reached evidence-store creation.
- TDD green: work-management service tests passed (6 tests).
- TDD red: checked-in commissioning settings remained disabled.
- Focused adapter/service/settings suite after implementation and review: 21 passed.
- TDD review follow-up red: disabled reconciliation preview was not blocked when the shared disabled-mode branch was removed; restored guard made the regression green.
- JSON validation: `settings/work-management/github-projects.settings.json` valid.
- `pwsh -NoProfile -File scripts/change-workflow.ps1 check`: passed with only declared 058 paths.
- `git diff --check`: passed.
- `pwsh -NoProfile -File scripts/verify.ps1`: passed after review; pytest exit 0, Python syntax 212 files, change governance 60 claims, locked interpreter/dependencies/configuration and exact three-rule checks all green.
- Commit gate: rerun `pwsh -NoProfile -File scripts/verify.ps1` after this closeout reconciliation and require exit 0 before staging; preserve that final result in the pull-request evidence rather than editing the verified tree afterward.

## Review

- Blocking commissioning findings discovered and addressed: live provider read-shape incompatibility and unenforced read-only feature modes.
- Direct final-diff review found one coverage gap for the shared `disabled` feature branch; a red/green regression test was added and the focused suite returned green.
- Dedicated Codex reviewer backend was unavailable (`AGENT_BACKEND_UNAVAILABLE`), so no specialist-review pass is claimed; the repository review contract was performed directly against the full diff.
- No remaining Critical or Important findings were identified in the direct review.
- Deferred intentionally: write-side numeric Project item identifiers and all mutation enablement.

## Git and merge

- Branch: `change/058-work-management-commissioning`
- Worktree: `.work/worktrees/058-work-management-commissioning`
- Final verified branch head: `0c58e9c3c978256ec3abed72816e8674c44ff546`.
- Exact-head Work Management run #17: success.
- Pull request: #80, merged.
- GitHub merge commit: `94ebc6a9bf9e9090a5e218ff560593e24695b1fa`.
- Post-merge direct provider inventory: passed; remote Project state unchanged.
- Post-merge live composed inventory: pending runtime restart and vault unlock.
- Cleanup: intentionally pending until composed inventory passes.

## Recovery

- Revert the change or set work-management `enabled` back to `false`; this slice does not mutate GitHub Project data.

## Residual items

- Restart `kis-op` through the normal supervised startup flow, complete the required vault unlock, and run composed `project_management_inventory(project_id="kis-mcp")` before live P5 commissioning is declared complete.
- Only after that composed inventory passes should change 058 be marked closed and its merged worktree/branches be removed.
- Any later write enablement must first adapt and verify the pinned provider's numeric Project item write identifiers.
