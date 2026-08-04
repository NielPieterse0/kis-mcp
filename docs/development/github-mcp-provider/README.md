# GitHub MCP Provider

## Status

This module integrates the official `github/github-mcp-server` as a separate, operator-supervised connector provider.

Implemented and locally verified:

- strict JSON provider configuration;
- pinned official source revision;
- standalone stdio proxy endpoint;
- all configured official toolsets, currently `all`;
- environment-only token injection;
- approved private-repository scope enforcement for reads and writes;
- redacted health/readiness;
- generic provider registration;
- hash-verified operator installation;
- focused static smoke testing.

Not yet live-verified:

- launch of an installed official GitHub MCP executable;
- authenticated calls to GitHub;
- ChatGPT remote/tunnel composition.

The provider is intentionally independent of Discover. Discover may later consume normalized GitHub evidence through a separate adapter.

## Boundary

```text
ChatGPT or future platform composition
                |
                v
python -m kis_mcp.providers.github
                |
                +-- repository-scope middleware
                +-- kis_github_health
                |
                v
official github-mcp-server over stdio
                |
                v
approved GitHub repository
```

This is an approved external connector boundary. It does not run through Desktop Commander or `ThreeRuleMiddleware`, and it does not change HR-001, HR-002, or HR-003.

Repository scoping is connector authorization. It is not a fourth Work policy rule.

## Configuration

Canonical configuration:

```text
settings/providers/github-mcp.provider.json
```

The current configuration pins:

- source: `https://github.com/github/github-mcp-server`;
- source revision: `3778a41476e31a072430cfee7c5d31c5f72def60`;
- executable: `C:\Projects\.kis-mcp\github-mcp\github-mcp-server.exe`;
- token environment: `GITHUB_PERSONAL_ACCESS_TOKEN`;
- toolsets: `all`;
- approved repository: `NielPieterse0/kis-mcp`;
- unscoped identity tool: `get_me`.

The configuration must not contain a token, OAuth credential, private key, or GitHub App secret.

## Authentication

Use a fine-grained personal access token or GitHub App installation token whose GitHub-side resource access is limited to `NielPieterse0/kis-mcp` and whose permissions match the required operations.

Set the token only in the supervised process environment:

```powershell
$env:GITHUB_PERSONAL_ACCESS_TOKEN = '<operator-supplied-token>'
```

The provider forwards only basic process environment variables and the configured token variable. Health output reports only whether the token is present.

GitHub-side resource scoping remains required even with local middleware. Some official provider operations have no repository argument, so the token or App installation is the authoritative backstop against access to other repositories.

## Install the official executable

Acquire or build the official executable from the pinned upstream revision outside the normal Work path. Record its SHA-256, then install it without network access:

```powershell
pwsh -NoProfile -File .\scripts\install-github-mcp.ps1 `
    -SourceBinary 'C:\Projects\staging\github-mcp-server.exe' `
    -ExpectedSha256 '<64-character-sha256>'
```

The installer:

- performs no download;
- verifies the supplied executable before copying;
- installs only beneath `C:\Projects\.kis-mcp\github-mcp`;
- moves an existing executable to a timestamped recoverable backup;
- verifies the installed copy again.

The operator is responsible for establishing that the supplied executable came from the configured official source revision. SHA-256 verification proves consistency with the operator-approved artifact; it does not independently establish provenance.

## Start the standalone provider

After installing the official executable and setting the token:

```powershell
$env:UV_PROJECT_ENVIRONMENT = 'C:\Projects\.kis-mcp\python-env'
$env:UV_CACHE_DIR = 'C:\Projects\.kis-mcp\uv-cache'
uv run --offline --no-sync python -m kis_mcp.providers.github
```

The wrapper launches the official provider as:

```text
github-mcp-server.exe stdio --toolsets=all
```

This endpoint is not yet mounted into the main Desktop Commander gateway or the concurrent ChatGPT remote-commissioning runtime.

## Repository scope behavior

Calls are allowed only when all explicit repository targets normalize to an approved `owner/repo` identity.

Supported identity shapes include:

```text
owner/repo
https://github.com/owner/repo
https://api.github.com/repos/owner/repo
git@github.com:owner/repo.git
```

Repository search calls require an explicit qualifier:

```text
repo:NielPieterse0/kis-mcp
```

Calls targeting another repository, unqualified repository searches, and unknown unscoped operations fail with `GITHUB_REPOSITORY_SCOPE`.

The middleware does not remove official read or write tools from the catalogue. The same repository boundary applies to both.

## Verify

Static/focused verification:

```powershell
pwsh -NoProfile -File .\scripts\smoke-github-mcp.ps1
```

Require the executable and token to be present and validate executable startup:

```powershell
pwsh -NoProfile -File .\scripts\smoke-github-mcp.ps1 -RequireLive
```

`-RequireLive` performs a bounded live MCP commissioning pass. It initializes the wrapper and official provider, verifies the pinned `get_me`, `get_file_contents`, and `create_or_update_file` surface, calls `kis_github_health`, authenticates with `get_me`, and reads `README.md` from the first approved repository. It reports booleans only and does not print repository content or perform a write mutation.

Full repository verification remains:

```powershell
pwsh -NoProfile -File .\scripts\verify.ps1
```

## Upgrade

1. Review the official upstream change.
2. Update `source_revision` in the provider JSON.
3. Build or acquire the official executable for that revision.
4. Install it with the new operator-approved SHA-256.
5. Run focused and full verification.
6. Run live authenticated smoke tests against the approved private repository.
7. Review tool schema changes and repository-target argument forms before claiming the upgrade ready.

Do not use an unpinned branch or silently replace the executable during normal startup.
