# Change: Post Land Restart Receipt Compat

- **Change ID**: `233-post-land-restart-receipt-compat`
- **Risk Profile**: lean

## Outcome

Make post-land kis-dev restart receipt persistence compatible with the current PowerShell/.NET runtime and prove live restart evidence for the healthy replacement runtime.

## Scope and acceptance

- Implement only the paths declared in `scope.json`.
- Make restart receipt replacement compatible with Windows PowerShell 5.1 and `pwsh.exe` while preserving same-directory atomic replacement.
- Preserve `kis-dev`-only targeting and bounded fallback evidence.
- Live closeout must prove a fresh development runtime on port 8011 plus `state=launching` receipt evidence with exact `landed_sha` and synchronized `launched_sha` while that replacement launcher remains healthy.

## Implementation and verification

- Implementation notes: added one shared atomic replacement helper using `File.Replace` with a bounded `.previous` backup for existing targets and two-argument `File.Move` for first creation/race recovery; primary and fallback receipts use it.
- Focused checks: Windows PowerShell regression failed before the fix on the unsupported three-argument `File.Move`; `tests/projects/test_post_land_restart.py` now passes 31/31; `git diff --check` and `scripts/change-workflow.ps1 check` pass.
- Review findings: initial code-quality review was clean; test-quality concerns about mocked detach, atomic observability, and detach failure are covered by existing worker behavior tests plus repeated `.previous` replacement and Windows PowerShell detach-failure regressions. One later reviewer claim that module-level `SHA` was undefined was contradicted by source and the passing suite. Final aggregate/agent review attempts exhausted their deadline; the required manual exact-diff fallback found no blocking issue.
- Residual risk: live post-merge proof remains required after merge; `kis-op` is out of lifecycle scope.
- Closeout state: implementation complete; publication/landing/live verification pending.
