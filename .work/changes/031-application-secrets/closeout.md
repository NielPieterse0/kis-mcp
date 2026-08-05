# Application-Managed Secrets Closeout

- **Change ID**: `031-application-secrets`
- **Status**: Merged and closed
- **Branch**: `change/031-application-secrets`
- **Pull request**: `#42` merged into `main`
- **Reviewed head**: `040c4bc82964aeebd54561e885ff3c5040825649`
- **Merge commit**: `f159156358ac797b4b53632f5885e307bdceb5db`

## Delivered

- Added the shared-kernel `kis_mcp.secrets` package with strict `secret://` references, bounded contracts, status/error types, AES-256-GCM envelopes, Argon2id derivation, encrypted vault persistence, session locking, and internal plaintext resolution.
- Added fixed runtime storage beneath `C:\Projects\.kis-mcp\secrets` with `vault.json`, metadata-only `metadata.json`, and encrypted backup preservation before replacement.
- Added operator-supervised passphrase unlock and optional canonical base64 `KIS_MCP_VAULT_KEY` bootstrap. No self-unlocking key file was implemented.
- Added a local JSON-over-stdin Secrets CLI and PowerShell wrappers for initialization, setting values, unlock verification, and unlock-material rotation. Long-running launchers transfer interactive unlock data through an inherited anonymous pipe rather than command-line arguments or a passphrase environment variable.
- Added exactly three metadata-only MCP registrations: `kis_secret_status`, `kis_list_secret_references`, and `kis_lock_secrets`. No public operation accepts or returns plaintext.
- Migrated operation and development tunnel settings from `tunnel_credential_target` to canonical `tunnel_secret_ref` values and removed Windows Credential Manager calls from tunnel setup and startup paths.
- Added JSON schemas, development documentation, and test coverage for cryptographic integrity, malformed references, tampering, partial state, backups, key zeroing, environment scrubbing, script boundaries, and tunnel migration.
- Declared `cryptography==50.0.0` directly and updated the existing offline lockfile metadata.

## Verification

- Baseline before implementation: `pwsh -NoProfile -File .\scripts\verify.ps1` passed.
- Focused final suite: `pwsh -NoProfile -File .\scripts\run-secrets-tests.ps1 tests/test_startup_scripts.py tests/secret_vault tests/test_tunnel_scripts.py tests/test_remote_runtime.py tests/test_startup_hardening.py -q` passed.
- Lock consistency: `uv lock --check --offline` passed.
- Scope/governance: `pwsh -NoProfile -File .\scripts\change-workflow.ps1 check` passed with all changed paths inside the declared change scope.
- Canonical repository verification after current-`main` integration and startup hardening: `pwsh -NoProfile -File .\scripts\verify.ps1` passed. Evidence included 137 Python files compiled, the full pytest suite passing with two expected skips, exact three-rule configuration validation, locked interpreter/dependencies, clean repository line endings, and valid change governance.
- PR-completion review added strict persisted-contract type validation plus startup regression coverage for bootstrap and pipe failure scrubbing, active-service lifetime, runtime-failure cleanup, and preflight-before-unlock ordering.

## Security evidence

- AES-256-GCM uses a fresh 96-bit nonce for each encryption and authenticates the immutable envelope header as associated data.
- Interactive and bootstrap unlock material is processed through Argon2id with explicit persisted parameters and a fresh 128-bit salt.
- Wrong unlock material, ciphertext/header tampering, malformed base64, malformed decrypted references, malformed metadata references, and incomplete vault state fail closed with bounded errors that exclude plaintext.
- The process retains only the derived session key as a mutable byte buffer; `lock()` overwrites that buffer before releasing it. Decrypted payload byte buffers are overwritten after parsing.
- The launcher removes both `KIS_MCP_VAULT_KEY` and the anonymous-pipe handle variable from the process environment after successful unlock.
- PowerShell uses `Read-Host -AsSecureString`, temporary BSTR conversion with `ZeroFreeBSTR`, redirected standard input for one-shot commands, and an inherited anonymous pipe for long-running startup.
- If startup handoff fails after spawning a child, the helper terminates and disposes the child rather than leaving an orphan process.
- Metadata and public tools expose only initialization/lock state, algorithms, generation, counts, references, and timestamps.

## Known boundary and deferred integration

This slice removes Windows Credential Manager from the tunnel credential path, but it does **not** yet remove the existing Supabase provider's Windows keyring implementation. Change `026-commissioning-refresh` is closed. The remaining integrations stay deferred because they are outside this change's approved scope; additionally, active change `040-context7-serena-adapters` owns `src/kis_mcp/server.py`, while active change `039-documentation-reconciliation` owns `SPEC.md` and `docs/OPERATIONS.md`.

Explicit follow-up work through later bounded changes:

- Mount metadata-only Secrets tools in `src/kis_mcp/server.py` after change `040` releases the path.
- Integrate NVIDIA as the first provider consumer of `SecretsService.resolve`.
- Migrate Supabase token storage from Windows keyring to canonical Secrets references.
- Reconcile `SPEC.md` and `docs/OPERATIONS.md` through change `039` or after it releases those authority paths.

Until that follow-up lands, the repository-wide statement “kis-mcp has no Windows credential dependency” is not yet true. The new Secrets kernel and tunnel migration are complete and verified within this slice's safe ownership boundary.

## Residual risks

- A process with equivalent operating-system access can inspect unlocked process memory. This design reduces exposure surfaces but cannot defend against an equally privileged local process.
- Environment bootstrap is weaker than supervised unlock because the bootstrap value exists in the parent/launcher environment before consumption.
- Managed runtimes may create short-lived immutable string copies while decoding standard-input JSON. The implementation minimizes lifetime and references but cannot guarantee complete memory erasure.
- Loss of all valid external unlock material is unrecoverable by design.

## Recovery

Revert the change commits and restore the prior tunnel settings/scripts if integration must be rolled back. Preserve `C:\Projects\.kis-mcp\secrets`, `vault.json`, and encrypted backups as recoverable artifacts; do not permanently delete vault state. A prior backup remains useful only with its corresponding passphrase or bootstrap material.
