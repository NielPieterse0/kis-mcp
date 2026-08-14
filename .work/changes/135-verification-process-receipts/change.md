# Change: Verification Process Receipts

- **Change ID**: `135-verification-process-receipts`
- **Risk Profile**: lean

## Outcome

Reconcile started verification processes through terminal exit evidence within one bounded timeout budget so intermediate output cannot produce false incomplete receipts.

## Scope and acceptance

- Implement only the paths declared in `scope.json`.
- Re-poll a started verification process when intermediate output arrives before the terminal KIS exit marker.
- Bound every follow-up read by the remaining portion of the caller's original timeout; never multiply the verification timeout.
- Preserve existing pass/fail/incomplete classification semantics once terminal evidence is available or the budget expires.

## Implementation and verification

- Implementation notes: replaced the single `read_process_output` follow-up with a deadline-bounded receipt loop keyed by the original `timeout_ms`.
- Focused checks: new intermediate-output regression failed before the fix; full verification-execution test module passes 7/7 after the fix.
- Review findings: NVIDIA test-quality review failed with upstream 502 and the independent Codex CLI review backend also failed; final exact-diff manual review found no blocking issue. The deadline starts before process launch, follow-up reads receive only the remaining original budget, and existing nonzero/missing-marker classification code is unchanged.
- Residual risk: runner implementations are still trusted to honor each supplied remaining timeout and return fresh process evidence.
- Closeout state: implementation complete; review, scope validation, exact-head CI, landing, and live regression commissioning pending.
