# Closeout: Deterministic Housekeeping

## Implemented scope

- Reconstructed the retained deterministic housekeeping package from historical Change 176 / PR #327 as fresh governed Change 194 code on current `main`.
- Added typed preview/apply and manual/scheduled trigger contracts, bounded deterministic receipts, governed local source-binding discovery, and a provider-neutral operation invoker.
- Added Work Management reconciliation and backlog-readiness runners with fail-closed incomplete evidence, exact issue dependency parsing, open/unclaimed readiness preconditions, bounded/idempotent apply, and typed apply failures.
- Added `scripts/housekeeping.py` as a host-neutral CLI that routes both runners through the same state machine.
- Did not restore local/VM/VirtualBox execution authority or modify Actions workflows.

## Validation evidence

- Focused checks: `uv run pytest tests/housekeeping -q` -> 30 passed.
- Lint/compile: Ruff clean; `python -m py_compile scripts/housekeeping.py` green; CLI `--help` green.
- Diff integrity: `git diff --check` green.
- Diff scope check: `pwsh -File scripts/change-workflow.ps1 check` green on all 14 declared changed paths.
- Live preview smoke exercised fail-closed authority behavior when a standalone provider instance lacked Project read capability; no mutation was attempted.

## Review

- Required review: code-quality; final exact-diff pass is run after this closeout snapshot and before commit publication.
- Additional architecture review: clean; no obsolete execution architecture or authority-direction violation found.
- Additional test-quality review generated concrete coverage findings; all actionable findings were implemented as regressions. Two final retry attempts failed only their structured-output contract, not verification.
- Resolved findings included apply-exception handling, readiness precondition authority, bounded dependency evidence, idempotency, transition-gate rejection, authority failures, duplicate bindings, missing Ready metadata, claimed/closed work, open/failed dependencies, early dependency-scan termination, and CLI runner parity.

## Git and merge

- Base: verified `main` / `origin/main` `cea1858252b1dbda88304dd6a0346d1107a799b7`.
- Branch: `change/194-deterministic-housekeeping`.
- Worktree: `.work/worktrees/194-deterministic-housekeeping`.
- Commit/PR/merge/cleanup are established after this immutable source snapshot by the governed exact-head publication and closeout workflow; no metadata-only source commit is required after landing.

## Residual items

- The standalone local preview correctly fails closed if its mounted GitHub provider does not expose the Project inventory methods needed by Work Management. Programme execution can use repository issues directly and does not depend on that optional Project surface. No unsafe fallback or guessed mutation path was added.
