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

- Implementation notes: lifecycle decision and direct `exit_once_through` response now agree on `manual_governed_change_closeout`, the current governed-change step, the full required sequence, and the no-reentry/no-PR-before-implementation flags.
- Focused checks: direct exit contract regression plus lifecycle/once-through focused tests pass locally; change governance check passes.
- Review findings: bounded contract reconciliation only; no once-through workflow stage was added.
- Residual risk: none identified for this bounded contract mismatch.
- Closeout state: ready for publication, exact-head GitHub Actions, merge, and cleanup.
