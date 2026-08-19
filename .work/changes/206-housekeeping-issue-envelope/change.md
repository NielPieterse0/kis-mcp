# Change: Housekeeping Issue Envelope

- **Change ID**: `206-housekeeping-issue-envelope`
- **Risk Profile**: lean

## Outcome

Normalize GitHub issue-read provider envelopes before housekeeping lifecycle-state evaluation so reconciliation and backlog-readiness can consume complete source evidence without weakening fail-closed behavior.

## Scope and acceptance

- Implement only the paths declared in `scope.json`.
- GitHub issue-read payloads wrapped as provider `text` JSON must be normalized before lifecycle-state evaluation.
- Missing or malformed source lifecycle state must remain fail-closed.
- Existing direct structured issue-read payloads and bulk open-issue inventory behavior must remain valid.
- Both housekeeping runners must complete live after merge; commissioning still requires final natural scheduled success.

## Implementation and verification

- Implementation notes: normalize exact issue reads through the existing provider JSON decoder and reject unusable lifecycle-state evidence.
- Focused checks: provider-envelope regressions red before implementation; full housekeeping + runtime suite green; Ruff and `git diff --check` green.
- Review findings: pending final specialist/base review.
- Residual risk: provider contract drift remains fail-closed; legacy Work Management findings are reported, not normalized.
- Closeout state: implementation complete; review/publication/commissioning pending.
