# Closeout: Runtime Authority Defender Conformance

## Implemented scope

- Added `settings/runtime-authority.settings.json` for explicit shared Python/Node and supervised uv ownership/trust policy.
- Added `scripts/runtime-authority.ps1` to verify the configured Python version/PSF signature and Node/OpenJS signature.
- KIS bootstrap now binds uv to that exact Python with managed-Python disabled and quarantines an incompatible generated venv before rebuild.
- Serena acquisition/candidate creation now uses the same verified host Python and persists its provenance.
- Current architecture and operator runbooks distinguish runtime provenance from native execution trust.

## Candidate/runtime evidence

- Verified Python: `C:\Users\piete\AppData\Local\Programs\Python\Python311\python.exe`, 3.11.9, Authenticode Valid, Python Software Foundation.
- Verified Node: `C:\nvm4w\nodejs\node.exe`, Authenticode Valid, OpenJS Foundation.
- Current `uv`: `C:\Users\piete\.local\bin\uv.exe`, classified `shared_operator_bootstrap`; authoritative acquisition remains required for install/upgrade and relocation is not accepted as trust remediation.
- Candidate env: `C:\Projects\.kis-mcp\temp\change-268-python-candidate`, base prefix is the verified shared-system Python.
- Candidate native Python artifacts: 65; Authenticode status alone is not treated as execution-trust acceptance.
- Node native helpers inventoried separately: 5 (`sharp` plus DBHub `cpu-features`/`ssh2` artifacts).

## Validation evidence

- Focused candidate tests: `49 passed` across runtime-authority, Serena/provider, and startup suites.
- Candidate dependency construction: locked environment built successfully with `--python <verified 3.11> --no-managed-python`; key native imports succeeded.
- Fresh Code Integrity window began `2026-08-30T15:33:09.5335812Z`; Operational log IDs 3033/3077: `0` total events during the observed candidate workload window.
- Existing live Serena wrapper smoke has an application-contract failure (`_SharedProviderClient.protocol_version`), and the standalone historical smoke assumes an unregistered temporary project. Neither produced Code Integrity events; they are not classified as Defender/runtime-trust failures.
- Repository verification and final governance: pending final tree.

## Review

- Findings: pending final substantive review.
- Resolutions: pending.

## Git and merge

- Branch: `change/268-runtime-authority-defender-conformance`
- Worktree: `.work/worktrees/268-runtime-authority-defender-conformance`
- Commit: pending
- Pull request or merge: pending
- Cleanup: pending

## Residual items

- The currently running KIS process still uses the pre-change generated 3.13 uv-managed environment; live replacement is intentionally deferred until landed-code commissioning so this active tool session is not broken mid-change.
- Commodity `.venv` remediation is excluded and remains commodity-owned.
