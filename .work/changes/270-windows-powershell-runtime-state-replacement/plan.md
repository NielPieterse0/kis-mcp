# Windows PowerShell Runtime-State Replacement Plan

**Goal:** Restore the landed independent `kis-dev` recovery path on Windows PowerShell.

## Constraints

- Stay inside `scope.json`.
- Preserve atomic replacement semantics.
- Test the failing Windows PowerShell runtime directly.
- Do not restart, stop, or mutate `kis-op` runtime availability.

## Implementation

- [x] Reproduce the unsupported three-argument `File.Move` failure.
- [x] Replace it with a Windows PowerShell-compatible atomic replacement API.
- [x] Add direct `powershell.exe` regression coverage.
- [ ] Run focused verification, governance, review, publish, exact-head CI, merge, and live recovery acceptance.