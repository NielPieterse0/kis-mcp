# Instance Startup Lifecycle Hardening Closeout

Status: implementation verified

Remote publication and post-merge live `kis-dev` commissioning are reported separately. This committed closeout does not claim future GitHub or credential-gated runtime state.

## Implemented

- Added `scripts/startup-instance-lifecycle.ps1` as the focused selected-instance ownership and recovery module.
- Starting `operation` evaluates/reclaims only operation identity and port 8010; starting `development` evaluates/reclaims only development identity and port 8011.
- Reclamation requires positive canonical Python/instance or tunnel/profile/endpoint identity. Unrelated listeners fail with PID/process diagnostics and are never terminated.
- Replaced parent-only launcher shutdown with full owned process-tree termination, closing the orphan-child path that could leave a stale listener after launcher exit.
- Added post-start proof that the newly created selected server process owns the configured listener before readiness.
- Added per-instance authoritative `current.json` lifecycle state: `restarting`, `preflight_failed`, `startup_failed`, `ready`, and `stopped`.
- Added recoverable quarantine for repository-local `.venv` and `.pytest_cache` transients while retaining the canonical external Python environment.
- Preserved timestamped runtime/log evidence independently from current ownership state.
- Reconciled `docs/OPERATIONS.md` after change 058 released its unused claim on that file.
- Kept HR-001, HR-002, and HR-003 unchanged.

## Verification

Focused startup/tunnel tests:

```powershell
pwsh -NoProfile -File scripts/run-secrets-tests.ps1 tests/test_startup_scripts.py tests/test_tunnel_scripts.py -q
```

Result: 38 passed.

Scope check:

```powershell
pwsh -NoProfile -File scripts/change-workflow.ps1 check
```

Result: exit code 0; every changed path is inside the 059 claim.

Canonical repository gate on the final executable state:

```powershell
pwsh -NoProfile -File scripts/verify.ps1
```

Result: exit code 0. Repository line endings, exact three-rule configuration, canonical interpreter, FastMCP 3.4.4, pytest 8.4.2, Python syntax, change governance, and the complete pytest suite all passed with the repository's two expected skips.

## Review

Direct review covered selected-instance isolation, positive ownership proof, process-tree cleanup, stale/current lifecycle accuracy, recoverable transient handling, PowerShell empty/root process sets, policy boundaries, tests, and operations documentation.

The optional `review_change_with_agent` reviewer could not run because its configured backend returned `404 Link not found`; this is recorded as a reviewer availability limitation, not treated as a passing independent review. No blocking finding remains from the direct review and fresh automated verification.

## Pre-commissioning runtime evidence

Before merge delivery, bounded listener capture reported:

- port 8010: `operation`, PID `21156`, canonical external Python, created 2026-08-07 11:20:41 local time;
- port 8011: no listener.

The primary checkout's old `.venv` was already absent. The remaining primary `.pytest_cache` was moved recoverably into KIS quarantine record `eed17277f4174e5097eb08b82ed9924c`.

Per operator instruction, live `kis-dev` startup is performed once from merged `main`, with the operator entering the vault unlock locally. That commissioning check must verify that 8010 remains owned by the existing operation runtime while 8011 becomes a fresh development runtime and its `current.json` matches the actual listener/process tree.

## Recovery

Revert the feature commit or merged pull request. Startup transient cleanup is recoverable because `.venv` and `.pytest_cache` are moved beneath the KIS quarantine root with metadata rather than permanently deleted. An unrelated port owner is never killed automatically.

## Residual risks

- Live credential-gated development startup is intentionally not claimed by repository verification and remains the immediate post-merge commissioning check.
- The optional advisory review backend currently returns `404 Link not found` and requires separate provider/agent diagnosis if independent agent review is desired.
