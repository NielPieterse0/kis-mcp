# Application-Managed Secrets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Every behavioral task follows test-driven development and records red/green evidence.

**Goal:** Add a recoverable local encrypted vault, supervised unlock, internal secret-reference resolution, metadata-only MCP registration, and tunnel credential migration away from Windows Credential Manager.

**Architecture:** A shared-kernel `kis_mcp.secrets` package separates strict references, cryptography, persistence, service/session state, public metadata contracts, MCP registration, and a local CLI. PowerShell scripts remain thin operator/runtime adapters and transfer secrets only through standard input or a process environment bootstrap. Active provider/server/documentation claims are not crossed.

**Tech Stack:** Python 3.11–3.13, `cryptography==50.0.0`, AES-256-GCM, Argon2id, JSON, FastMCP 3.4.4, PowerShell 7, pytest, Git worktrees.

## Global constraints

- Stay inside `scope.json`.
- All repository and runtime writes remain beneath `C:\Projects`.
- No external network access.
- Preserve prior encrypted vault versions; no permanent deletion.
- No plaintext-returning or plaintext-accepting MCP tool.
- No secret or passphrase in command-line arguments, logs, metadata, exceptions, or checked-in settings.
- Support supervised passphrase and `KIS_MCP_VAULT_KEY`; do not implement `master.key`.
- Do not modify active provider, Tools, Discover, server, policy, `SPEC.md`, or `docs/OPERATIONS.md` claims.

---

### Task 1: Register change and verify baseline

**Files:**
- Create: `.work/changes/031-application-secrets/{scope.json,spec.md,plan.md,tasks.md,closeout.md}`

**Produces:** A validated rigorous change record and clean baseline evidence.

- [ ] Run `pwsh -NoProfile -File .\scripts\change-workflow.ps1 validate` and confirm the new scope does not overlap active changes.
- [ ] Run `pwsh -NoProfile -File .\scripts\verify.ps1` before implementation and record the exact result.
- [ ] Review this plan against the specification for omissions, placeholders, inconsistent names, and unsafe assumptions.

### Task 2: Define references and metadata contracts

**Files:**
- Create: `tests/secret_vault/test_references.py`
- Create: `tests/secret_vault/test_contracts.py`
- Create: `src/kis_mcp/secrets/errors.py`
- Create: `src/kis_mcp/secrets/references.py`
- Create: `src/kis_mcp/secrets/contracts.py`
- Create: `src/kis_mcp/secrets/status.py`
- Create: `src/kis_mcp/secrets/__init__.py`
- Create: `contracts/secrets/vault-envelope.schema.json`
- Create: `contracts/secrets/vault-metadata.schema.json`

**Interfaces:**
- Produces: `SecretReference.parse(value: str) -> SecretReference`, `.uri`, `.path`; immutable `KdfParameters`, `VaultEnvelope`, `VaultMetadata`, `SecretReferenceRecord`, and `SecretsStatus` contracts.

- [ ] Write failing tests for canonical references and rejection of traversal, empty segments, backslashes, query/fragment content, malformed schemes, and excessive length.
- [ ] Run the focused tests and confirm failure because the package/interfaces do not exist.
- [ ] Implement the smallest strict reference parser, errors, dataclasses, and JSON schemas.
- [ ] Run focused tests and confirm pass.
- [ ] Refactor names/serialization while keeping tests green.

### Task 3: Implement authenticated cryptography

**Files:**
- Create: `tests/secret_vault/test_crypto.py`
- Create: `src/kis_mcp/secrets/crypto.py`
- Modify: `pyproject.toml`
- Modify: `uv.lock`

**Interfaces:**
- Consumes: `KdfParameters`, `VaultEnvelope`.
- Produces: `derive_key(passphrase: bytes, salt: bytes, parameters: KdfParameters) -> bytes`, `encrypt_payload(plaintext: bytes, key: bytes, *, salt: bytes, parameters: KdfParameters) -> VaultEnvelope`, `decrypt_payload(envelope: VaultEnvelope, key: bytes) -> bytes`, and `envelope_associated_data(...) -> bytes`.

- [ ] Write failing tests for roundtrip, wrong key, tampered ciphertext, tampered authenticated header, fresh nonce, and invalid key length.
- [ ] Run focused tests and confirm expected missing-interface failures.
- [ ] Declare `cryptography==50.0.0` directly and update the lockfile offline.
- [ ] Implement Argon2id key derivation, AES-256-GCM encryption/decryption, strict base64 decoding, and authenticated canonical header data.
- [ ] Run focused tests and confirm pass.
- [ ] Run dependency/lock consistency verification.

### Task 4: Implement atomic encrypted vault persistence

**Files:**
- Create: `tests/secret_vault/test_vault.py`
- Create: `src/kis_mcp/secrets/vault.py`

**Interfaces:**
- Produces: `VaultStore(root: Path)`, `.initialize(envelope, metadata)`, `.load_envelope()`, `.load_metadata()`, `.replace(envelope, metadata)`, `.paths`, and encrypted backup preservation.

- [ ] Write failing tests for bounded root paths, initialization, strict JSON parsing, atomic replacement, metadata minimization, encrypted backup creation, and refusal to overwrite an initialized vault through initialize.
- [ ] Run focused tests and confirm expected failures.
- [ ] Implement atomic temporary writes with `os.replace`, `fsync` where supported, deterministic JSON, and backup-before-replace behavior.
- [ ] Run focused tests and confirm pass.
- [ ] Refactor persistence helpers while retaining failure-path coverage.

### Task 5: Implement the session SecretsService

**Files:**
- Create: `tests/secret_vault/test_service.py`
- Create: `src/kis_mcp/secrets/service.py`

**Interfaces:**
- Produces: `SecretsService.initialize(passphrase, initial_secrets=None)`, `.unlock(passphrase)`, `.unlock_with_key(key)`, `.lock()`, `.status()`, `.list_references()`, `.resolve(reference)`, `.set_secret(reference, value)`, and `.rotate_master_key(new_passphrase)`.

- [ ] Write failing tests for initialize/unlock/resolve, locked-state rejection, missing reference, metadata-only list/status, set/replace with backup, wrong passphrase, raw-key bootstrap, rotation, and best-effort mutable key zeroing.
- [ ] Run focused tests and confirm expected failures.
- [ ] Implement the minimal thread-safe service with canonical JSON plaintext payload and no plaintext in exceptions/status.
- [ ] Run focused tests and confirm pass.
- [ ] Add tests that scan serialized vault/metadata and exception text for known secret/passphrase markers.

### Task 6: Add metadata-only MCP registration

**Files:**
- Create: `tests/secret_vault/test_tools.py`
- Create: `src/kis_mcp/secrets/tools.py`

**Interfaces:**
- Produces: `register_secret_tools(server: FastMCP, service: SecretsService) -> None` registering exactly `kis_secret_status`, `kis_list_secret_references`, and `kis_lock_secrets`.

- [ ] Write failing tests that inspect registered names and schemas and prove there is no get/set/resolve plaintext operation or secret-valued parameter.
- [ ] Run focused tests and confirm expected failures.
- [ ] Implement the three metadata-only operations.
- [ ] Run focused tests and confirm pass.
- [ ] Record that mounting into `server.py` remains deferred by scope and is currently coordinated through change `040-context7-serena-adapters`.

### Task 7: Implement the local Secrets CLI and PowerShell operator scripts

**Files:**
- Create: `tests/secret_vault/test_cli.py`
- Create: `tests/secret_vault/test_scripts.py`
- Create: `src/kis_mcp/secrets/cli.py`
- Create: `scripts/secret-vault.ps1`
- Create: `scripts/initialize-secret-vault.ps1`
- Create: `scripts/set-secret.ps1`
- Create: `scripts/rotate-secret.ps1`
- Create: `scripts/unlock-secrets.ps1`
- Create: `settings/secrets.settings.json`
- Create: `docs/development/secrets/README.md`

**Interfaces:**
- Produces local CLI commands: `initialize`, `status`, `list`, `set`, `resolve-internal`, `rotate`, and `verify-unlock`; sensitive input is newline-delimited standard input and output for `resolve-internal` is restricted to local script consumption.

- [ ] Write failing CLI tests using subprocess standard input for passphrases/secrets and asserting arguments, stdout/stderr, metadata, and files contain no sensitive markers.
- [ ] Write failing source-contract tests for secure PowerShell prompts, no secret command arguments, no key file mode, and state root confinement.
- [ ] Run focused tests and confirm expected failures.
- [ ] Implement the CLI and thin PowerShell wrappers.
- [ ] Run focused tests and confirm pass.
- [ ] Document threat model, bootstrap weakness, backup/recovery, and deferred integrations in non-authoritative development documentation.

### Task 8: Migrate tunnel credential configuration and scripts

**Files:**
- Modify: `settings/kis-mcp.settings.json`
- Modify: `src/kis_mcp/config.py`
- Modify: `scripts/tunnel-state.ps1`
- Modify: `scripts/set-tunnel-credential.ps1`
- Modify: `scripts/setup-tunnel.ps1`
- Modify: `scripts/start-chatgpt.ps1`
- Modify: `scripts/start.ps1`
- Modify: `tests/test_tunnel_scripts.py`
- Modify: `tests/test_remote_runtime.py`
- Modify: `tests/test_startup_hardening.py`
- Modify/Create: `tests/test_config.py`

**Interfaces:**
- Replaces: `tunnel_credential_target` with `tunnel_secret_ref`.
- Consumes: local Secrets CLI through `scripts/secret-vault.ps1`.

- [ ] Update tests first to require canonical `secret://tunnel/<instance>/authentication-token` references and reject Windows Credential Manager imports/calls.
- [ ] Run affected tests and confirm they fail against existing settings/scripts/config.
- [ ] Update settings and config contracts.
- [ ] Update tunnel setup/start/set scripts to use the local encrypted vault and operator-supervised unlock without command-line secret exposure.
- [ ] Run affected tests and confirm pass.
- [ ] Search the owned runtime path set for remaining `tunnel_credential_target`, `Get-KisMcpWindowsCredential`, and `Set-KisMcpWindowsCredential` dependencies and eliminate them.

### Task 9: Security review, full verification, and integration readiness

**Files:**
- Modify: `.work/changes/031-application-secrets/tasks.md`
- Modify: `.work/changes/031-application-secrets/closeout.md`

- [ ] Review the full diff against every requirement and acceptance criterion, including crypto misuse, path traversal, race/atomicity, metadata leakage, subprocess exposure, exception leakage, and scope discipline.
- [ ] Run all focused Secrets and affected tunnel/config tests.
- [ ] Run Python compilation for changed modules.
- [ ] Run `pwsh -NoProfile -File .\scripts\change-workflow.ps1 check`.
- [ ] Run the canonical `pwsh -NoProfile -File .\scripts\verify.ps1` serially on the final branch head.
- [ ] Record exact commands, outcomes, skipped integration items, rollback, and residual risks.
- [ ] Commit the final verified change, push the branch, open a PR, and report the exact head for operator review; do not merge without explicit authorization.
