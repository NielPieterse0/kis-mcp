# Application-Managed Secrets

This document describes the development contract for the kis-mcp encrypted local vault. It is not yet the authoritative operator guide; `SPEC.md` and `docs/OPERATIONS.md` are currently owned by change `039-documentation-reconciliation` and must be reconciled there or after that claim closes.

## Boundary

The Secrets module is a shared kernel service under `src/kis_mcp/secrets`. Providers and runtime adapters consume canonical references such as:

```text
secret://providers/nvidia/api-key
secret://tunnel/operation/authentication-token
```

Checked-in JSON stores references only. Plaintext resolution is internal and requires an unlocked process-local `SecretsService`.

Runtime state is fixed beneath:

```text
C:\Projects\.kis-mcp\secrets\
├── vault.json
├── metadata.json
└── backups\
```

`vault.json` is an AES-256-GCM envelope. Interactive unlock material is processed with Argon2id using the salt and parameters stored in the envelope. `metadata.json` contains only generation, timestamps, and reference names.

## Threat model

The design protects secrets at rest from accidental viewing, repository exposure, logs, tool transcripts, and ordinary inspection of settings. It does not defend against a process running with equivalent filesystem and process-memory access while the vault is unlocked.

The decryption material must originate outside the encrypted vault:

- Recommended: operator-supervised `Read-Host -AsSecureString` unlock at startup.
- Optional automation: canonical base64 32-byte material in `KIS_MCP_VAULT_KEY`.
- Not implemented: a self-unlocking `master.key` file stored beside the vault.

Environment bootstrap is weaker than interactive unlock because the key exists in the child process environment until the launcher consumes and removes it. It is an explicit automation trade-off, not equivalent protection.

## Operator commands

Initialize an empty vault:

```powershell
pwsh -NoProfile -File .\scripts\initialize-secret-vault.ps1
```

Set or replace one canonical reference:

```powershell
pwsh -NoProfile -File .\scripts\set-secret.ps1 `
  -Reference 'secret://providers/nvidia/api-key'
```

Rotate the interactive unlock material:

```powershell
pwsh -NoProfile -File .\scripts\rotate-secret.ps1
```

Verify that the supplied unlock material opens the vault:

```powershell
pwsh -NoProfile -File .\scripts\unlock-secrets.ps1
```

`unlock-secrets.ps1` is a one-shot verification command. A separate process cannot retain a session key for a later kis-mcp process. `start.ps1` and `start-chatgpt.ps1` perform the persistent process-local unlock required by the running gateway.

Set tunnel credentials through the vault:

```powershell
pwsh -NoProfile -File .\scripts\set-tunnel-credential.ps1 `
  -Instance operation
```

## Sensitive data transport

Operator scripts do not place passphrases or secret values in command-line arguments. Local maintenance commands transfer a bounded JSON payload over redirected standard input. Long-running startup transfers the unlock payload through an inherited anonymous pipe identified by a non-secret handle environment variable.

PowerShell converts `SecureString` values through a temporary BSTR and calls `ZeroFreeBSTR`. Python and PowerShell may still create short-lived immutable string objects while decoding JSON; the implementation minimizes lifetime and references but cannot guarantee memory erasure in managed runtimes.

## Public MCP surface

The module defines exactly three metadata-only registrations:

```text
kis_secret_status
kis_list_secret_references
kis_lock_secrets
```

No public tool accepts a secret value, passphrase, bootstrap key, or reference to resolve. No public tool returns plaintext.

Mounting these registrations in `src/kis_mcp/server.py` is deferred until active change `040-context7-serena-adapters` releases that path.

## Recovery and backups

Before replacing an initialized vault during a secret update or unlock rotation, kis-mcp copies the prior encrypted `vault.json` into `backups`. Backups are never decrypted automatically and are not permanently deleted by vault operations.

Loss of all valid external unlock material is unrecoverable by design. Recovery requires a compatible encrypted backup and its corresponding passphrase or bootstrap material.

## Deferred integrations

The following work remains intentionally excluded from this slice because it is outside the approved change scope, with shared surfaces still coordinated through active changes:

- Mount metadata-only tools into `server.py` after change `040-context7-serena-adapters` releases the path.
- Make NVIDIA the first provider consumer of `SecretsService.resolve` through a bounded provider integration change.
- Migrate Supabase provider credentials from keyring storage through a bounded provider integration change.
- Reconcile `SPEC.md` and `docs/OPERATIONS.md` through change `039-documentation-reconciliation` or after it releases those authority paths.

These items must be implemented through later scoped changes rather than broadening this merge-ready slice.
