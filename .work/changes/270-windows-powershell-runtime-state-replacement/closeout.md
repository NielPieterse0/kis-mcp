# Closeout: Windows PowerShell Runtime-State Replacement

## Implemented scope

- Replaced unsupported three-argument `System.IO.File.Move` overwrite with `System.IO.File.Replace` for existing runtime-state files.
- Retained two-argument `File.Move` for first-write state creation.
- Added direct `powershell.exe` regression coverage for repeated atomic state writes.

## Delivery

- Issue: #602.
- Parent acceptance: #600.
- Pending governed verification, review, exact-head CI, merge, live `kis-dev` recovery acceptance, and cleanup.