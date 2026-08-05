# GitHub MCP Provider

## Status

The official `github/github-mcp-server` is integrated as an operator-supervised external connector and mounted into the shared `kis-mcp` runtime under the `github_*` namespace.

Implemented and live verified:

- pinned official immutable release `v1.8.0` at commit `ca8ab52dcc45b86fae190398178fd22edb7b1362`;
- published release-asset SHA-256 verification and bounded Windows installation;
- official built-in browser OAuth with no PAT forwarded by KIS;
- stateful upstream stdio session for process-lifetime OAuth tokens;
- approved private-repository read and write surface;
- local repository-scope rejection for unapproved repositories;
- shared-runtime mounting and namespaced tool exposure;
- redacted installation, PAT-conflict, and unverified-authentication health states.

OAuth tokens remain in the official provider process. Restarting the provider normally requires another interactive authorization. No token, authorization code, client secret, or OAuth state is stored in repository JSON.

When the executable and local configuration are present, `kis_provider_status` reports **`Ready — authentication required`**. This is the normal pre-authentication state: the provider is installed, configured, and mountable, but the current process has not yet proved OAuth identity, upstream connectivity, tool discovery, or live operation. A sign-in requirement is not a degraded or broken provider state.

## Boundary

```text
ChatGPT / shared kis-mcp runtime
                |
                +-- github_* namespace
                +-- GitHubRepositoryScopeMiddleware
                |
                v
stateful official GitHub MCP stdio process
                |
                +-- browser OAuth / device fallback
                |
                v
approved GitHub repository
```

This connector does not run through Desktop Commander Work networking and does not change HR-001, HR-002, or HR-003. Repository scope is connector authorization, not a fourth Work policy rule.

## Configuration

Canonical configuration:

```text
settings/providers/github-mcp.provider.json
```

Pinned values:

- source: `https://github.com/github/github-mcp-server`;
- release: `v1.8.0`;
- commit: `ca8ab52dcc45b86fae190398178fd22edb7b1362`;
- executable: `C:\Projects\.kis-mcp\github-mcp\github-mcp-server.exe`;
- authentication mode: `oauth`;
- PAT conflict variable: `GITHUB_PERSONAL_ACCESS_TOKEN`;
- toolsets: `all`;
- approved repository: `NielPieterse0/kis-mcp`;
- unscoped identity tool: `get_me`.

`pat_env` identifies a conflicting environment override. KIS deliberately removes that variable from the provider process so the official OAuth flow cannot be silently replaced by PAT authentication. Live auth and smoke scripts fail with `GITHUB_OAUTH_PAT_CONFLICT` when it is set.

## Install

Run the supervised bootstrap installer:

```powershell
pwsh -NoProfile -File .\scripts\install-github-mcp.ps1
```

The installer:

1. loads the pinned release tag and commit from strict JSON;
2. fetches the exact GitHub release and tag metadata;
3. requires a stable immutable release;
4. resolves annotated tags to the pinned commit;
5. selects exactly one Windows x86-64 ZIP asset;
6. requires and verifies the release asset's published `sha256:` digest;
7. extracts exactly one `github-mcp-server.exe`;
8. stages the binary under `C:\Projects\.kis-mcp\github-mcp`;
9. moves an existing executable to a timestamped `.backup.exe` file before replacement;
10. moves installation workspace artifacts into recoverable quarantine rather than permanently deleting them.

The installer reports release, commit, asset, published digest, archive hash, binary hash, destination, and backup path. It never prints credentials.

## Authenticate

Clear any PAT override, then run:

```powershell
Remove-Item Env:GITHUB_PERSONAL_ACCESS_TOKEN -ErrorAction SilentlyContinue
pwsh -NoProfile -File .\scripts\auth-github-mcp.ps1
```

The official provider opens GitHub authorization in the browser and can fall back to device authorization. The commissioning command then proves:

- required `get_me`, `get_file_contents`, and `create_or_update_file` tools exist;
- OAuth identity succeeds through `get_me`;
- `README.md` can be read from `NielPieterse0/kis-mcp`;
- `github/github-mcp-server` is rejected by local repository-scope middleware.

No write mutation is performed by commissioning.

## Shared-runtime smoke

Offline provider tests and preflight:

```powershell
pwsh -NoProfile -File .\scripts\smoke-github-mcp.ps1
```

Authenticated shared-runtime verification:

```powershell
pwsh -NoProfile -File .\scripts\smoke-github-mcp.ps1 -RequireLive
```

The live path builds the normal shared `kis-mcp` server, verifies `kis_provider_status` reports GitHub mounted, then exercises `github_get_me` and `github_get_file_contents` through the namespaced catalogue. It also proves local out-of-scope rejection.

## Repository scope

Explicit repository targets normalize to approved `owner/repo` identities. Supported forms include:

```text
owner/repo
https://github.com/owner/repo
https://api.github.com/repos/owner/repo
git@github.com:owner/repo.git
```

Repository search requires an explicit approved `repo:` qualifier. Calls targeting another repository, unqualified searches, and unknown unscoped operations fail with `GITHUB_REPOSITORY_SCOPE`.

The middleware does not remove official read or write tools. The same approved-repository boundary applies to both.

## Recovery and upgrade

- Roll back an installation by moving the timestamped `.backup.exe` to the configured executable path after preserving the current binary.
- Installation workspaces are retained beneath `C:\Projects\.kis-mcp\quarantine\github-mcp-install`.
- To upgrade, review the official release, update the exact tag and commit in both JSON and schema, rerun the installer, focused tests, full verification, OAuth commissioning, and shared-runtime smoke.
- Do not use `latest`, an unpinned branch, a PAT fallback, or silent startup installation.
