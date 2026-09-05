# Change: Manual Exit Standard Governed Flow

- **Change ID**: `646-manual-exit-standard-governed-flow`
- **Risk Profile**: lean

## Outcome

Make once-through manual exit continue through the standard governed implementation, PR, exact-head CI, merge, and cleanup path instead of implying PR-only closeout.

## Scope and acceptance

- Manual exit disables once-through progression without marking the work blocked.
- If no governed change exists, the next required step is to create one and implement the requested outcome.
- If a governed change exists, resume that standard governed change workflow.
- PR, exact-head GitHub Actions, merge readiness, merge, main refresh, and cleanup remain mandatory.
- Do not re-enter once-through solely because the handoff was unbound when manual exit occurred.

## Implementation and verification

- Implementation notes: lifecycle decision now returns `manual_governed_change_closeout` with an explicit standard governed sequence and current required step.
- Focused checks: lifecycle and once-through focused tests passed locally; change governance check passed.
- Review findings: bounded contract clarification only; broader reversible checkpoint work remains #707.
- Residual risk: `exit_once_through` immediate response still uses the older PR-closeout label until the follow-up tool-response alignment lands; lifecycle decision is authoritative for current progression.
- Closeout state: publication and exact-head GitHub Actions remain.
