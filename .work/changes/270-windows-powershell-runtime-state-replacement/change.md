# Change: Windows PowerShell Runtime-State Replacement

- **Change ID**: `270-windows-powershell-runtime-state-replacement`
- **Risk Profile**: small deployment fix

## Outcome

Restore `kis-dev` recovery on Windows PowerShell by replacing an unsupported atomic state-write API overload with a compatible implementation.

## Scope and acceptance

- Modify only `scripts/startup-instance-lifecycle.ps1`, `tests/test_startup_scripts.py`, and this change record.
- Preserve atomic replacement semantics for existing runtime-state files.
- Preserve first-write behavior for absent runtime-state files.
- Direct regression coverage must pass under both `pwsh` and `powershell.exe`.
- Live post-land recovery must restart only `kis-dev` and verify the landed source revision.
- `kis-op` runtime availability must remain untouched.

## Implementation and verification

- Existing state replacement uses `System.IO.File.Replace` with a temporary backup path compatible with Windows PowerShell/.NET Framework.
- Focused startup/recovery tests pass.
- Exact-head CI and live recovery acceptance remain required before #600 can close.