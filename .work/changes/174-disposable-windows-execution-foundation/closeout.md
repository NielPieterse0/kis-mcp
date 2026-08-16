# Closeout: Disposable Windows Execution Foundation

## Implemented scope

- Added provider-neutral execution request/result/readiness/lifecycle contracts plus JSON schemas and runner settings.
- Preserved public verification on `local-process`; added a separate internal exact-source Hyper-V proof adapter.
- Added disabled-by-default `windows-hyperv-proof` with exact source/profile/image/toolchain binding, bounded receipts, fresh attempt state, and fail-closed lifecycle results.
- Guest input is an exact Git archive; mutable host checkout, KIS state, operator profile, and secrets are not mounted into the guest.
- Normal Hyper-V retirement is HR-003-compatible: stop, disable auto-start, disconnect networking, rename into quarantine, and retain recoverable state rather than permanently deleting through Work.

## Validation evidence

- Focused suite: `uv run pytest -q tests/execution tests/workflows/verification` -> 52 passed.
- Hard-rule/middleware regressions: `uv run pytest -q tests/test_p1_command_hardening.py tests/test_middleware.py` -> 68 passed.
- Bytecode compilation: `uv run python -m compileall -q src/kis_mcp/execution src/kis_mcp/workflows/verification` -> passed.
- Governance: `pwsh -NoProfile -File scripts/change-workflow.ps1 check` -> passed on the exact committed tree.
- Diff integrity: `git diff HEAD^ HEAD --check` -> passed; worktree remained clean.
- Live host readiness: `Get-Command Get-VMHost` -> unavailable, exit 2; no supervised live guest run or performance measurement is claimed. That commissioning evidence is now tracked in follow-up issue `#330` and is not required to land this implementation foundation.

## Review

- Bounded architecture specialist review after the cleanup/provenance correction returned no findings on the execution boundary.
- Dedicated safety/security specialist retries remained unavailable at the reviewer-provider boundary (502/process failures); this is recorded as reviewer infrastructure failure, not a clean specialist result.
- Required exact-diff security fallback found and fixed: host state outside `C:\Projects`, HR-003-incompatible shell deletion cleanup, repeated-request mutable-state/receipt reuse, and guest network exposure before execution.
- Final manual architecture/security re-check plus executable architecture and hard-rule guards found no remaining blocking issue in the bounded slice.

## Git and merge

- Branch: `change/174-disposable-windows-execution-foundation`
- Worktree: `.work/worktrees/174-disposable-windows-execution-foundation`
- Base: `9adf1ca26a6a96a173605a7e5dd5c11216d6ec0e`
- Local implementation commit: `815dff3b70b2c7f9e2425475cdb098ace86ed152`; closeout evidence is committed separately on the same governed branch.
- Pull request: `#329` is open on the registered review branch. The aggregate PR-preparation wrapper returned 502, but the same governed KIS reconcile/create primitives succeeded; no raw GitHub publication path was used.
- Exact-head Actions: the provider-native `windows-latest` job currently fails before runner assignment (`runner_id: 0`) and exposes no job log, so no test failure is attributed to this change.
- Merge: implementation scope is complete; landing is now blocked only by the repository-required exact-head GitHub Actions gate.
- Work Management: change 174 no longer depends on Hyper-V host availability. Live commissioning moved to follow-up issue `#330`; `#324` should advance out of On Hold once its projection is reconciled.
- `SPEC.md`: bounded current-product reconciliation completed after change 171 released the path through merged PR `#312`.
- Cleanup: not eligible before verified merge.

## Residual gates and follow-up

- Follow-up issue `#330` owns supervised Hyper-V execution of an existing declared verification plus live startup/setup/verification/transfer measurements on a Hyper-V-capable host. It is commissioning work, not a change-174 landing gate.
- Exact-head GitHub Actions remains the sole landing gate and is infrastructure-blocked before runner assignment by the account billing/spending-limit state; no implementation test failure is claimed from that run.
- Canonical GitHub Actions routing, GitHub runner registration, `actions/scaleset`, and `import-isolate` integration remain explicitly out of scope for this slice.
