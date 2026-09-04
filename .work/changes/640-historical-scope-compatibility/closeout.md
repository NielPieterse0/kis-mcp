# Closeout: Historical Scope Compatibility

## Implemented scope

Historical schema-v4 file loading receives a bounded in-memory compatibility projection; current schema-v4 creation/direct parsing remains strict, and current-change `check` resolves only its exact scope.

## Verification

- Compatibility RED→GREEN tests: passed.
- Full `tests/test_change_governance.py`: 53/53 passed.
- KIS scope `check`: passed.
- Real commodity #289 strict integration `check`: passed with the modified KIS engine.
- Ruff was not available in the shared focused-test runtime; configured KIS/CI verification remains authoritative for that check.
- Provider exact-head CI: pending publication.

## Review

- First Codex review found one High and one Medium: compatibility was too broad for active schema-v4 claims, and a legacy dependency token could disappear silently.
- Both findings were corrected: compatibility now requires landed/retired topology plus the scope record on the base branch; unmerged malformed schema-v4 claims remain strict. Unresolved legacy dependency tokens are retained as structured compatibility warnings.
- Corrected exact-commit code-quality re-review: 0 findings; prior High/Medium closed.
- API-contract review then found a Medium/Low test-contract gap around CLI warning/error serialization; exact `validate` success/error contract tests and complete warning-order assertions were added and are green.
- Final API re-review found one Low: multi-warning CLI ordering was not locked end-to-end. The CLI success test now emits two warnings and asserts the exact ordered JSON array; 53/53 tests remain green.
- Final exact-commit API re-review after that test-only correction: pending.

## Safety / authority

- No historical repository scope is rewritten.
- Compatibility cannot create modern dependency/ownership authority from legacy tokens.
- Current and unmerged active schema-v4 validation remains fail-closed.
- Compatibility warnings make any projected legacy metadata explicit.
- Cleanup/merge semantics are unchanged.

## Residual

Historical stale branches/worktrees remain a separate cleanup/disposition problem after the reader can inventory them safely.
