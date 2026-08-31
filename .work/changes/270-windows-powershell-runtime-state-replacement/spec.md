# Change Specification: Windows PowerShell Runtime-State Replacement

- **Change ID**: `270-windows-powershell-runtime-state-replacement`
- **Status**: Active
- **Complexity**: small
- **Risk triggers**: deployment

## Outcome

Restore `kis-dev` recovery under supported Windows PowerShell by replacing the unsupported three-argument `File.Move` call with a compatible atomic replacement primitive.

## Requirements

- **REQ-001**: existing runtime-state files must be atomically replaced without relying on a .NET API overload unavailable to Windows PowerShell.
- **REQ-002**: first-write behavior must remain supported.
- **REQ-003**: regression coverage must execute the replacement path through `powershell.exe`, not only `pwsh`.
- **REQ-004**: post-land recovery must successfully restart only `kis-dev`; `kis-op` runtime availability must remain untouched.