# Closeout: Historical Scope Compatibility

## Implemented scope

Historical schema-v4 file loading receives a bounded in-memory compatibility projection; current schema-v4 creation/direct parsing remains strict, and current-change `check` resolves only its exact scope.

## Verification

- Compatibility RED→GREEN tests: passed.
- Real commodity #289 integration `check`: passed with modified KIS engine.
- Full change-governance tests / Ruff: pending.
- KIS implementation review/verification and provider exact-head CI: pending.

## Safety / authority

- No historical repository scope is rewritten.
- Compatibility cannot create modern dependency/ownership authority from legacy tokens.
- Current change validation remains fail-closed.
- Cleanup/merge semantics are unchanged.

## Residual

Historical stale branches/worktrees remain a separate cleanup/disposition problem after the reader can inventory them safely.
