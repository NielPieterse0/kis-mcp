# Application-Managed Secrets

This document describes the development contract for the kis-mcp encrypted local vault and its process-scoped startup handoff. `SPEC.md` and `docs/OPERATIONS.md` remain the authoritative current implementation and operator guides.

## Boundary

The Secrets module is a shared kernel service under `src/kis_mcp/secrets`. Providers and runtime adapters consume canonical references such as:

```text
secret://provider/nvidia-nim/api-key
secret://provider/dockerhub/pat
secret://database/example/connection
secret://tunnel/operation/authentication-token
```

Checked-in JSON stores references only. Plaintext resolution from the encrypted vault is internal and requires verified runtime unlock material. The tunnel runtime uses the canonical tunnel reference to derive a per-user Windows Credential Manager target. Ordinary gateway startup unlocks the application vault only when a configured provider reference actually requires resolution; the current local College DBHub binding and Docker Hub public mode require no provider secret. ChatGPT startup already unlocks for NVIDIA NIM and reuses that same verified payload for any configured DBHub/Docker Hub references.

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

The decryption material for explicit vault operations must originate outside the encrypted vault:

- Interactive maintenance: operator-supervised `Read-Host -AsSecureString` unlock for initialize, set, rotate, or verification commands.
- Optional vault-backed automation: canonical base64 32-byte material in `KIS_MCP_VAULT_KEY` for a consumer that explicitly requires vault resolution.
- Not implemented: a self-unlocking `master.key` file stored beside the vault.

`start.ps1` resolves provider references only when strict JSON contains them; otherwise it does not unlock the vault for providers. `start-chatgpt.ps1` reads the verified runtime unlock for NVIDIA NIM and reuses that in-process payload for any configured DBHub/Docker Hub references rather than decrypting twice. Resolved values are injected only into the owned server process under internal KIS environment names, removed from `ProcessStartInfo` after spawn, and cleared from the parent hashtable. Environment bootstrap remains a weaker option for explicit vault-backed automation because the key exists in the child process environment until consumed and scrubbed.

## Operator commands

Initialize an empty vault:

```powershell
pwsh -NoProfile -File .\scripts\initialize-secret-vault.ps1
```

Set or replace one canonical reference:

```powershell
pwsh -NoProfile -File .\scripts\set-secret.ps1 `
  -Reference 'secret://provider/nvidia-nim/api-key'
```

Rotate the interactive unlock material:

```powershell
pwsh -NoProfile -File .\scripts\rotate-secret.ps1
```

Verify that the supplied unlock material opens the vault:

```powershell
pwsh -NoProfile -File .\scripts\unlock-secrets.ps1
```

`unlock-secrets.ps1` is a one-shot verification command. A separate process cannot retain a session key for a later kis-mcp process, and normal gateway startup deliberately does not keep the vault unlocked.

Set or replace the tunnel control-plane credential in the current user's Windows Credential Manager entry:

```powershell
pwsh -NoProfile -File .\scripts\set-tunnel-credential.ps1 `
  -Instance operation
```

## Sensitive data transport

Operator scripts do not place passphrases or secret values in command-line arguments. Vault maintenance commands transfer a bounded JSON payload over redirected standard input. Runtime provider resolution uses the verified current-user unlock credential and internal process-scoped environment handoff only; DBHub external DSNs are translated to child `DBHUB_DSN`, and Docker Hub PAT mode is translated to child `HUB_PAT_TOKEN`. The canonical vault reference and plaintext value are never written into generated provider TOML or checked-in provider/project JSON.

Tunnel credential updates use `Read-Host -AsSecureString` and `CredWriteW`. Startup retrieves the selected Generic Credential with `CredReadW`, copies it only into the owned tunnel-client process environment, and clears the parent-side reference after process creation. PowerShell converts `SecureString` values through a temporary BSTR and calls `ZeroFreeBSTR` on writes.

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
