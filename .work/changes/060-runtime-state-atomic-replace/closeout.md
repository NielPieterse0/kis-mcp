# Runtime State Atomic Replace Closeout

Status: implementation verified

Remote publication and post-merge live `kis-dev` commissioning are reported separately. This closeout does not claim credential-gated runtime commissioning before that evidence exists.

## Root cause

The merged 059 lifecycle writer created a sibling temporary JSON file and used:

```powershell
[System.IO.File]::Replace($Temporary, $Path, $null)
```

when `current.json` already existed. In the active PowerShell/.NET runtime, the null backup-path argument raises `The path is empty. (Parameter 'path')`. This blocked a repeated development startup while updating the preflight `restarting` state.

## Implemented scope

- Added a real two-write regression test through `Write-KisMcpAtomicJson`.
- Changed only the existing-destination branch to:

```powershell
[System.IO.File]::Move($Temporary, $Path, $true)
```

- Preserved the sibling temporary-file pattern, public function interface, lifecycle state model, instance ownership rules, process reclamation rules, and the three-rule policy unchanged.

## TDD evidence

RED:

```powershell
pwsh -NoProfile -File scripts/run-secrets-tests.ps1 tests/test_startup_scripts.py -q
```

Before the production edit, the new test failed because the first document remained persisted: expected `2`, actual `1`.

GREEN focused startup/tunnel verification:

```powershell
pwsh -NoProfile -File scripts/run-secrets-tests.ps1 tests/test_startup_scripts.py tests/test_tunnel_scripts.py -q
```

Result: 39 passed.

## Repository verification

Scope:

```powershell
pwsh -NoProfile -File scripts/change-workflow.ps1 check
```

Result: exit code 0; all changed paths are within the 060 claim.

Canonical repository gate:

```powershell
pwsh -NoProfile -File scripts/verify.ps1
```

Result: exit code 0. Repository line endings, configuration, exact HR-001/HR-002/HR-003 policy, canonical interpreter, dependencies, Python syntax, change governance, and the full pytest suite passed with the repository's two expected skips.

## Review

Direct review covered the exact diff, overwrite semantics, sibling temporary-file behavior, scope discipline, lifecycle invariants, and policy neutrality. No blocking finding remains.

A dedicated reviewer subagent is not available in this chat runtime, so no independent subagent review is claimed.

## Recovery

Revert the focused implementation commit. Runtime `current.json` is generated operational state and can be rewritten by the next supervised startup.

## Residual item

After merge and primary-main verification, rerun `start-chatgpt.ps1 -Instance development` while leaving `kis-op` untouched. Commissioning must prove that the existing development process is reclaimed, a fresh 8011 listener is created, `development/current.json` reaches `ready`, and the operation listener/PID remains unchanged.
