# Change: Post Land Restart Receipt Ownership

- **Change ID**: `234-post-land-restart-receipt-ownership`
- **Risk Profile**: lean

## Outcome

Prevent stale post-land kis-dev restart workers from overwriting the canonical latest receipt for a newer landing, then live-prove ordered restart evidence.

## Scope and acceptance

- Implement only the paths declared in `scope.json`.
- Serialize canonical restart-receipt updates and require worker-state ownership by landed SHA plus worker PID.
- Preserve atomic replacement, Windows PowerShell 5.1/`pwsh.exe` compatibility, and `kis-dev`-only lifecycle targeting.
- Live closeout must prove the corrected runtime on 8011 and canonical receipt ownership after flushing the one pre-fix bootstrap worker.

## Implementation and verification

- Implementation notes: `latest.json` updates are serialized through an exclusive lock bounded by both a five-second deadline and 100 retry attempts; `scheduled` acquires ownership, later states require the same landed SHA and worker PID, and a superseded worker exits before synchronization or launch side effects.
- Focused checks: the two stale-generation cases failed before implementation and now pass; the regression also proves no `.previous` replacement occurs when ownership is lost; the full `tests/projects/test_post_land_restart.py` module passes 33/33; `git diff --check` and governed scope check pass.
- Review findings: initial review prompted the independent retry-count bound and the stronger stale-worker early-exit behavior. Final code-quality re-review is clean. A test-quality warning that the stale-generation regression did not prove rejection was rejected: the test asserts both an unchanged newer receipt and exit code `0` while no settings file exists, so any execution past the ownership check would fail before Git/runtime effects. Other suggestions to weaken the exclusive file lock or add stale-lock deletion are not applicable: `FileShare.None` provides the synchronization invariant and Windows releases the file handle when a process terminates.
- Residual risk: the landing that introduces this fix is scheduled by the pre-fix runtime/script; closeout therefore includes one explicit bootstrap retrigger under the landed runtime so the lingering pre-fix worker is retired before future landings rely on the ownership guard.
- Closeout state: implementation complete; review/publication/landing/live verification pending.
