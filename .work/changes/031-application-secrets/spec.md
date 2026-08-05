# Change Specification: Application-Managed Secrets

- **Change ID**: `031-application-secrets`
- **Status**: Approved for implementation by operator request
- **Risk Profile**: rigorous
- **Development level**: Complex — security-sensitive persistent state, startup behavior, credential migration, and shared-kernel interfaces

## Outcome

Replace kis-mcp's tunnel dependency on Windows Credential Manager with a local encrypted JSON vault under `C:\Projects\.kis-mcp\secrets`, unlocked through an operator-supervised passphrase or an explicitly configured environment bootstrap. Expose only metadata and lock operations to MCP clients; plaintext resolution remains an internal service operation.

## Authority and scope

- Authoritative sources: operator request of 2026-08-05, `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, `docs/OPERATIONS.md`, and `policy/kis-mcp.policy.json`.
- Owned paths: see `scope.json`.
- Excluded active claims: provider implementations, Tools module, Discover, `src/kis_mcp/server.py`, `SPEC.md`, and `docs/OPERATIONS.md`.
- Dependency: `026-commissioning-refresh` was the implementation-order dependency for provider, server, and authoritative documentation surfaces and is now closed; this slice still does not broaden into those deferred integrations.
- Integration owner: none. Deferred integration must be recorded, not silently implemented across active claims.

## Architecture

The Secrets module is a shared kernel service under `src/kis_mcp/secrets`, not a Provider or Tool implementation. The encrypted vault stores one authenticated JSON payload using AES-256-GCM. A 256-bit key is derived from an interactive passphrase using Argon2id, or supplied as an explicitly approved base64 bootstrap key through `KIS_MCP_VAULT_KEY`. The service keeps only derived key material in process memory and zeroes its mutable session buffer on lock.

The encrypted envelope is versioned and self-describing:

```json
{
  "version": 1,
  "cipher": "AES-256-GCM",
  "kdf": "argon2id",
  "kdf_parameters": {
    "iterations": 3,
    "memory_cost_kib": 65536,
    "lanes": 4,
    "length": 32
  },
  "salt": "base64",
  "nonce": "base64",
  "ciphertext": "base64"
}
```

Runtime storage:

```text
C:\Projects\.kis-mcp\secrets\
├── vault.json
├── metadata.json
└── backups\
```

`metadata.json` may contain reference names, timestamps, schema version, generation, and counts. It must never contain secret values, plaintext hashes, passphrases, derived keys, nonces reused for encryption, or command-line secret material.

## Requirements

- **REQ-001 — Boundary**: All vault state, temporary files, and backups remain beneath `C:\Projects\.kis-mcp\secrets` and all repository changes remain beneath `C:\Projects`.
- **REQ-002 — Cryptography**: Encrypt vault payloads with AES-256-GCM and derive interactive keys with Argon2id using explicit persisted parameters and a fresh random salt and nonce.
- **REQ-003 — Authentication**: Bind the immutable envelope header as authenticated associated data so changes to version, cipher, KDF, or KDF parameters fail closed.
- **REQ-004 — References**: Accept only canonical `secret://` references with bounded slash-separated segments; reject traversal, empty segments, query strings, fragments, backslashes, and malformed schemes.
- **REQ-005 — Session lock**: Plaintext resolution requires an unlocked service. Locking clears the mutable session key buffer and prevents further resolution until a successful unlock.
- **REQ-006 — No plaintext MCP output**: The module may register only metadata operations equivalent to `kis_secret_status`, `kis_list_secret_references`, and `kis_lock_secrets`. No MCP-facing operation may accept a secret value or return plaintext.
- **REQ-007 — Local operator writes**: Vault initialization, secret set, and master-key rotation occur through local operator scripts and a non-MCP Python CLI. Secret values and interactive passphrases are supplied over standard input, never command-line arguments.
- **REQ-008 — Unlock modes**: Support supervised interactive passphrase unlock and `KIS_MCP_VAULT_KEY` base64 32-byte bootstrap key. Do not implement a self-unlocking `master.key` file.
- **REQ-009 — Atomicity and recovery**: Replace vault and metadata files atomically. Before replacing an existing encrypted vault, preserve the prior encrypted file under `backups` with a collision-resistant timestamp/generation name. Never permanently delete prior encrypted versions.
- **REQ-010 — Metadata minimization**: List and status operations expose only initialization, lock state, envelope version/algorithms, generation, and canonical references.
- **REQ-011 — Tunnel migration**: Replace `tunnel_credential_target` with `tunnel_secret_ref` in canonical settings and configuration. Tunnel setup/start scripts resolve the secret through the local Secrets CLI and must not source or call `windows-credential.ps1`.
- **REQ-012 — Startup supervision**: Startup scripts prompt with `Read-Host -AsSecureString` when no bootstrap key is present, pass unlock material without command-line exposure, and preserve it only for the child processes that require it.
- **REQ-013 — Direct dependency**: Declare `cryptography==50.0.0` directly because the Secrets module imports its AES-GCM and Argon2id APIs.
- **REQ-014 — Internal consumption seam**: Provide a typed internal `SecretsService.resolve(reference)` interface suitable for NVIDIA, OpenAI, tunnel, and future provider adapters without exposing plaintext through MCP.
- **REQ-015 — Deferred integration**: Do not modify provider, Tools, server, `SPEC.md`, or `docs/OPERATIONS.md` integration surfaces within this slice. Record server mounting, NVIDIA consumption, Supabase migration, and authoritative documentation reconciliation as explicit later scoped changes.
- **REQ-016 — Logging**: Exceptions and status output may identify a canonical reference but must never include the supplied secret, passphrase, derived key, decrypted payload, or environment bootstrap value.

## Acceptance

1. **Given** an uninitialized state directory, **when** the operator initializes the vault with a passphrase, **then** `vault.json` and metadata are created beneath the configured secrets root and no plaintext appears in either file.
2. **Given** a valid vault, **when** the correct passphrase unlocks it, **then** an internal consumer can resolve an existing canonical reference and receives the expected value in memory.
3. **Given** a wrong passphrase or modified envelope/header/ciphertext, **when** unlock is attempted, **then** the operation fails with a bounded integrity/unlock error and exposes no plaintext.
4. **Given** an unlocked service, **when** it is locked, **then** resolution fails until another successful unlock and the prior mutable key buffer is zeroed best-effort.
5. **Given** a secret replacement or master-key rotation, **when** the new vault is committed, **then** the prior encrypted vault remains recoverable beneath `backups`.
6. **Given** public tool registration, **when** registered tool names and schemas are inspected, **then** only status, list-reference, and lock operations exist and no input/output field can carry a secret value.
7. **Given** canonical remote settings, **when** tunnel scripts are inspected and exercised with a test vault, **then** they use `tunnel_secret_ref`, never import Windows Credential Manager support, and do not place secrets in process arguments.
8. **Given** `KIS_MCP_VAULT_KEY`, **when** bootstrap unlock is used, **then** a valid base64 32-byte key unlocks the vault and malformed values fail closed without echoing the value.
9. **Given** the repository verification workflow, **when** focused and full checks run on the final branch head, **then** all tests, compile checks, governance checks, and line-ending checks pass.

## Risks and recovery

- **Risk — unrecoverable passphrase loss**: The vault cannot securely recover without external key material. Recovery is restoring a prior encrypted backup and supplying its correct passphrase/key; no bypass is implemented.
- **Risk — process-memory access**: A process with equivalent OS access may inspect runtime memory. The design limits exposure duration and surfaces but cannot defend against a fully equivalent local process principal.
- **Risk — key and ciphertext co-location in environment mode**: Environment bootstrap is weaker than supervised unlock. It is explicit, optional, and documented as reduced protection.
- **Risk — script integration regression**: Tunnel startup is covered by source-contract and focused behavior tests. Revert the branch or restore prior settings/scripts if commissioning fails.
- **Risk — cryptographic format drift**: Version and algorithms are strict; unknown versions or parameters fail closed. Existing encrypted backups are preserved.
- **Recovery**: Revert the change commit(s), restore the previous settings/scripts, and retain encrypted vault/backups as recoverable artifacts. Do not permanently delete vault state.

## Out of scope

- Self-unlocking key files or automatic permanent key storage.
- Public plaintext retrieval or secret-setting MCP tools.
- Networked vault services, HSMs, TPM sealing, DPAPI, or Windows Credential Manager.
- Provider implementation changes; NVIDIA and Supabase consumption remain separate bounded integrations.
- Actual NVIDIA provider implementation while active Tools/Provider claims exist.
- Supabase OAuth/keyring migration in this slice.
- Direct `server.py` mounting and authoritative `SPEC.md`/`docs/OPERATIONS.md` reconciliation until their active claim closes.
