# GitHub OAuth Commissioning Closeout

## Status

Ready for commit and pull request.

## Outcome

Slice B installs and commissions the pinned official GitHub MCP Windows release with built-in interactive OAuth, preserves the existing approved-repository middleware, and proves the provider through the shared `kis-mcp` runtime.

Completed behavior:

- official immutable release `v1.8.0` pinned to commit `ca8ab52dcc45b86fae190398178fd22edb7b1362`;
- GitHub release and tag metadata validation;
- published release-asset SHA-256 verification;
- bounded Windows ZIP extraction and recoverable executable replacement;
- no PAT forwarding or credential persistence in repository files;
- explicit PAT-conflict diagnostics;
- stateful upstream stdio session required for process-lifetime OAuth;
- standalone browser OAuth commissioning;
- approved private-repository `README.md` read;
- explicit `GITHUB_REPOSITORY_SCOPE` proof for an unapproved repository;
- shared-runtime `github_*` mount and live tool exposure;
- truthful local readiness separated from live authentication;
- provider-specific operations and verification documentation.

## Governance

The merged `008-github-mcp-provider` record was still marked `active`, so the normal validator correctly rejected Slice B's successor ownership. Slice 018 explicitly owns and closes that one stale claim. No validator logic was weakened and no unrelated active claim was modified.

Final claim validation reports 12 valid claims.

## Installer evidence

Observed successful installation:

```text
release:          v1.8.0
commit:           ca8ab52dcc45b86fae190398178fd22edb7b1362
asset:            github-mcp-server_Windows_x86_64.zip
archive SHA-256:  C91ECA7FFD5492C2B273DFCC8747D4B54AFDDCDE342704572A6917C73757F608
binary SHA-256:   E8CF444BC58DD3A47938504D4D85E338D76BF558AF463D252CBC554CCAC4C256
destination:      C:\Projects\.kis-mcp\github-mcp\github-mcp-server.exe
```

The archive digest matched GitHub's published `sha256:` value. Temporary installation artifacts were moved into recoverable quarantine.

## Live OAuth evidence

Standalone commissioning exited `0` after the official provider opened GitHub authorization and reported completion.

Verified booleans:

```text
surface:                 true
authentication:          true
private_repository_read: true
repository_scope:        true
```

Approved repository: `nielpieterse0/kis-mcp`.

Rejected repository: `github/github-mcp-server` with explicit `GITHUB_REPOSITORY_SCOPE` evidence.

No write mutation was performed.

## Shared-runtime evidence

`pwsh -NoProfile -File .\scripts\smoke-github-mcp.ps1 -RequireLive` exited `0` and reported:

```text
focused_tests:                passed
live_ready:                   True
live_mounted:                 True
live_surface:                 True
live_authentication:          True
live_private_repository_read: True
live_repository_scope:        True
```

The smoke used the normal `build_server()` path and namespaced `github_*` tools. It did not modify shared runtime composition files.

## Test and review evidence

- 37 focused GitHub provider tests passed.
- Full repository pytest passed with two expected skips.
- 67 Python files passed syntax validation.
- Exact HR-001, HR-002, and HR-003 configuration checks passed.
- Final full repository verification returned `ok: true` after implementation and closeout documentation were complete.
- Whole-diff review found and repaired:
  - worktree package-resolution mismatch in operator scripts;
  - duplicate MCP initialization from the stateless proxy lifecycle;
  - false-positive scope proof when arbitrary upstream failures were accepted as containment.

Final full verification, JSON validation, whitespace validation, and scope enforcement were completed immediately before commit preparation.

## Credential handling

No token, OAuth state, authorization code, client secret, or private key is written to repository JSON or project files. `GITHUB_PERSONAL_ACCESS_TOKEN` is never forwarded by KIS and blocks commissioning when present. OAuth tokens remain in the official provider process and expire when that process ends.

## Recovery

- Existing binaries are moved to timestamped `.backup.exe` files before replacement.
- Installation workspaces are retained under `C:\Projects\.kis-mcp\quarantine\github-mcp-install`.
- Rollback requires preserving the current executable and moving the selected backup into the configured path.
- Repository deletion remains recoverable through the MCP quarantine mechanism.

## Residual limitations

- OAuth must normally be repeated after provider restart because tokens are process-lifetime.
- `--toolsets=all` causes the official OAuth application to request broad scopes. Local middleware constrains explicit repository targets, but the official built-in OAuth application controls GitHub-side scope granularity.
- Desktop Commander string-form notification validation warnings remain visible during shared-runtime smoke. They are pre-existing and outside Slice B ownership.
