# GitHub OAuth Commissioning Specification

## Outcome

Replace the PAT-gated GitHub adapter with a pinned official Windows release that uses the official stdio server's built-in interactive OAuth flow. Prove authentication, approved private-repository access, local repository-scope rejection, and exposure through the shared kis-mcp runtime.

## Requirements

1. Pin official GitHub MCP Server release `v1.8.0` at commit `ca8ab52dcc45b86fae190398178fd22edb7b1362`.
2. Install only an immutable official GitHub release asset. Resolve the release through the GitHub REST API, verify the tag commit, select one Windows x86-64 ZIP asset, require its published SHA-256 digest, verify the downloaded archive, extract only `github-mcp-server.exe`, and replace an existing installation recoverably with a timestamped backup.
3. Store no token, client secret, authorization code, or OAuth state in repository JSON or project files.
4. Configure authentication as `oauth`. Do not forward `GITHUB_PERSONAL_ACCESS_TOKEN`; report its presence as a conflicting override and refuse live commissioning while it is set.
5. Treat executable presence and OAuth-safe environment as local readiness. Authentication and upstream connectivity remain live-session evidence, not static readiness.
6. Add an operator-supervised authentication command that starts the official stdio provider, triggers tool discovery, completes browser or device-code OAuth, calls `get_me`, reads `README.md` from `NielPieterse0/kis-mcp`, and proves a different repository is rejected by local scope middleware.
7. Upgrade the live smoke to perform the same authenticated checks through the shared `build_server()` catalogue using `github_*` namespaced tools, proving Slice A integration.
8. Preserve the existing repository-scope middleware and do not edit Work policy, Desktop Commander, Discover, Skills, Supabase, or the shared composition root.
9. Offline focused tests must not perform network access or open a browser. Live commissioning remains explicit through PowerShell switches/scripts.

## Architecture

```text
install-github-mcp.ps1
  -> GitHub immutable release metadata
  -> verify tag commit + release asset digest
  -> C:\Projects\.kis-mcp\github-mcp\github-mcp-server.exe

kis-mcp provider builder
  -> clean stdio environment without PAT
  -> github-mcp-server.exe stdio --toolsets=all
  -> official browser OAuth / device-code fallback
  -> GitHubRepositoryScopeMiddleware
  -> shared runtime namespace github_*
```

## Failure handling

- Missing or mismatched release metadata, tag commit, asset, digest, archive hash, executable, or destination boundary fails installation without replacing the current executable.
- PAT presence fails OAuth commissioning with a corrective message and is never forwarded.
- Provider build failure remains contained by the already-implemented runtime composer.
- Live smoke failures distinguish missing installation, OAuth/authentication failure, missing tools, approved-repository read failure, scope failure, and missing shared-runtime exposure.

## Verification

- Red/green focused tests for settings, schema, environment, readiness, installer, auth script, live smoke, and shared-runtime namespacing.
- Existing GitHub scope tests remain green.
- `scripts/smoke-github-mcp.ps1` passes offline.
- `scripts/smoke-github-mcp.ps1 -RequireLive` is run only when the installed binary and interactive operator OAuth are available.
- Full `scripts/verify.ps1`, syntax, JSON validation, diff check, and scope inspection pass on the final branch.

## Governance exception

The normal change validator currently recursively loads copied historical claims from every worktree and reports duplicate IDs, branches, outcomes, and path ownership. Slice 018 uses the AGENTS.md emergency path: a native isolated worktree plus explicit change artifacts before implementation edits. The pre-existing validator failure is recorded and no unrelated claim files are changed.

## Exclusions

PAT authentication, token persistence, GitHub App server-to-server authentication, Supabase OAuth, tunnel commissioning, provider-runtime redesign, retries, background monitoring, and automatic startup login are outside this slice.
