# Specification

## Problem

The post-land restart script writes atomic receipts with the three-argument `System.IO.File.Move(source, destination, overwrite)` overload. Windows PowerShell 5.1 does not expose that overload, so a direct hook invocation can schedule the detached `pwsh.exe` worker and restart `kis-dev` while the parent receipt write fails.

## Required behavior

- Receipt replacement must work under both Windows PowerShell 5.1 and `pwsh.exe`.
- Existing receipt files must be replaced atomically without a delete-then-move gap.
- Both primary and fallback receipt writers must use the same compatible replacement primitive.
- The hook remains scoped only to `kis-mcp/main` and launches only `kis-dev`; `kis-op` is never lifecycle-managed.

## Acceptance criteria

1. A regression test invoking the scheduler path through `powershell.exe` with an existing receipt passes and records `state=scheduled`.
2. Existing `pwsh.exe` worker-path tests continue to pass, including terminal receipt updates and `kis-dev`-only targeting.
3. After merge, a live hook trigger restarts the development runtime on port 8011; while the replacement launcher remains healthy, the latest receipt is `state=launching` with the exact `landed_sha` and synchronized `launched_sha` for that landing.
