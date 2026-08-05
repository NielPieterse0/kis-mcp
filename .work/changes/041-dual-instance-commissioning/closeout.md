# Closeout: Dual Instance Commissioning

## Implemented scope

- Added canonical external app identities to JSON configuration:
  - internal `operation` -> `kis-op` -> `127.0.0.1:8010`;
  - internal `development` -> `kis-dev` -> `127.0.0.1:8011`.
- Centralized selector normalization for `kis-op`, `op`, `operation`, `kis-dev`, `dev`, and `development`.
- Added structural validation for the exact app/instance/port mapping, loopback host, `/mcp` path, exact two-instance set, and duplicate ports.
- Removed the incorrect peer-instance listener prohibition while retaining selected-instance own-port exclusivity.
- Added app, canonical instance, and exact endpoint to startup readiness output and startup-state JSON.
- Preserved separate tunnel profiles, tunnel IDs, vault secret references, runtime directories, logs, and per-launcher process ownership.
- Updated `SPEC.md` and `docs/OPERATIONS.md` to describe concurrent `kis-op` and `kis-dev` operation through one launcher.

## Validation evidence

- Baseline repository verification before implementation: passed with the complete suite green and two expected skips.
- TDD RED: 16 focused failures demonstrated the missing app identities, selector aliases, exact port validation, concurrent-startup behavior, readiness identity, and current documentation drift.
- TDD GREEN: `tests/test_startup_scripts.py` and `tests/test_tunnel_scripts.py` passed: 28 tests, 0 failures.
- Full pytest evidence: 733 passed, 2 skipped in 99.03 seconds.
- Canonical repository verification: `pwsh -NoProfile -File scripts/verify.ps1` returned 0 and reported that the locked environment, approved Skills root, and exact three-rule implementation are consistent.
- Diff scope check: `pwsh -NoProfile -File scripts/change-workflow.ps1 check` passed with only declared paths.
- Port preflight while the operational tool remained in use:
  - `kis-op` was listening on `127.0.0.1:8010` through `kis_mcp.remote_runtime --instance operation`;
  - `127.0.0.1:8011` was free;
  - no operational process was stopped, restarted, or modified.

## Live commissioning

- A bounded `kis-dev` launch was attempted while `kis-op` remained active.
- The launcher correctly reached the supervised vault-unlock boundary before binding port `8011`.
- This MCP execution context could not expose an interactive desktop console for the vault prompt and did not inherit `KIS_MCP_VAULT_KEY`; therefore no secret was read, supplied, logged, or persisted.
- The attempted development launcher exited without binding `8011`; `kis-op` remained listening on `8010` throughout.
- Exact remaining operator smoke command:

```powershell
cd C:\Projects\kis-mcp
pwsh -NoProfile -File .\scripts\start-chatgpt.ps1 kis-dev
```

Enter the existing vault unlock when prompted, then confirm `kis-op` remains available and `kis-dev` reports `app=kis-dev`, `instance=development`, and `endpoint=http://127.0.0.1:8011/mcp`.

## Review

- Scope review: no HR policy, provider catalogue, tunnel ID, credential value, or automatic-failover behavior changed.
- Correctness review: peer-port activity is permitted; selected-port activity fails before vault unlock; aliases resolve to one canonical instance; invalid app/port mappings fail structurally.
- Security/secrets review: app identities and tunnel IDs are non-secret; secret references remain unchanged; no credential material entered the repository or logs.
- Recovery: stop only the newly started `kis-dev` launcher and revert this branch. The existing `kis-op` launcher is independently owned and remains outside rollback.
- Blocking findings: none in the implemented and automated scope.

## Git and merge

- Branch: `change/041-dual-instance-commissioning`
- Worktree: `.work/worktrees/041-dual-instance-commissioning`
- Commit: pending final commit
- Pull request: pending publication
- Cleanup: pending merge

## Residual items

- Live external tunnel readiness for `kis-dev` requires one operator-entered vault unlock in an interactive terminal. This is a commissioning prerequisite, not an implementation or verification failure.
