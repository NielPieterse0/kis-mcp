# Application-Managed Secrets Tasks

## Status

- [x] Operator approved the slice and architecture.
- [x] Isolated worktree `031-application-secrets` created from clean `main`.
- [x] Complex/rigorous classification recorded.
- [x] Change governance validates without overlap.
- [x] Clean baseline verification recorded.
- [x] Secret references and metadata contracts implemented test-first.
- [x] AES-256-GCM and Argon2id implementation completed test-first.
- [x] Atomic encrypted vault and backup behavior completed test-first.
- [x] Session `SecretsService` completed test-first.
- [x] Metadata-only MCP registration completed test-first.
- [x] Local Secrets CLI and operator PowerShell scripts completed test-first.
- [x] Tunnel credential dependency migrated away from Windows Credential Manager.
- [x] Focused security review completed.
- [x] Canonical repository verification passes on the reviewed branch content.
- [x] Branch pushed and draft PR #42 opened against `main`.

## Deferred integration ledger

- [ ] Mount metadata-only secret tools in `src/kis_mcp/server.py` after change `026` releases the path.
- [ ] Integrate NVIDIA as the first provider consumer after active Tools/Provider claims release their paths.
- [ ] Migrate Supabase token storage from Windows keyring after change `026` releases `providers/**`.
- [ ] Reconcile `SPEC.md` and `docs/OPERATIONS.md` after change `026` releases those authority paths.

## Verification evidence

- Baseline: `pwsh -NoProfile -File .\scripts\verify.ps1` passed before implementation.
- Focused final: `pwsh -NoProfile -File .\scripts\run-secrets-tests.ps1 tests/test_startup_scripts.py tests/secret_vault tests/test_tunnel_scripts.py tests/test_remote_runtime.py tests/test_startup_hardening.py -q` passed.
- Dependency lock: `uv lock --check --offline` passed.
- Governance: `pwsh -NoProfile -File .\scripts\change-workflow.ps1 check` passed with all changed paths inside scope.
- Canonical final: `pwsh -NoProfile -File .\scripts\verify.ps1` passed; 97 Python files compiled, the full pytest suite passed with two expected skips, line endings passed, and change governance passed.
