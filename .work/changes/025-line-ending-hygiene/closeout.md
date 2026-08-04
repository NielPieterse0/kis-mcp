# Closeout: Line Ending Hygiene

## Implemented scope

- Added `.gitattributes` with LF as the canonical text format, CRLF only for `.bat` and `.cmd`, and explicit binary handling.
- Added `.editorconfig` with UTF-8, LF, final-newline, and trailing-whitespace rules.
- Added `scripts/configure-repository.ps1` and invoked it from change creation and verification to enforce repository-local Git EOL settings.
- Added verification of policy files, effective local Git configuration, and actual `git ls-files --eol` index/worktree state.
- Renormalized the two CRLF blobs stored in the index and refreshed 387 LF-governed worktree files without adding semantic changes.

## Validation evidence

- TDD red: three focused tests failed because the policy files, parser, and verifier check were absent.
- TDD green: all 14 tests in `tests/test_repository_scope.py` passed.
- Full tests: 526 collected; 524 passed and 2 existing tests skipped.
- Whitespace: `git diff --cached --check` passed.
- Scope: `change-workflow.ps1 check` accepted exactly 14 changed paths.
- Canonical repository verification passed: zero EOL violations, 76 Python files parsed, 21 governance claims validated, and pytest exited 0.

## Review

- The two Desktop Commander contract files have no semantic diff with end-of-line whitespace ignored.
- No feature, provider, policy-rule, or active Discover/Supabase implementation path changed.
- Other active worktrees remained clean after the shared repository-local Git configuration was applied.

## Git and merge

- Branch: `change/025-line-ending-hygiene`
- Worktree: `.work/worktrees/025-line-ending-hygiene`
- Commit: use the final verified branch HEAD reported at handoff
- Pull request or merge: not yet requested
- Cleanup: after merge through `change-workflow.ps1 cleanup 025-line-ending-hygiene`

## Residual items

- Existing active worktrees receive the committed attributes when they next rebase or merge this branch; their current states were checked and remain clean.
