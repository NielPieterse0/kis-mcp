# GitHub MCP OAuth Commissioning Verification

## Scope

Verified branch: `change/018-github-oauth-commissioning`

Verified boundary:

- strict GitHub provider JSON and schema;
- official release installer;
- OAuth-only environment and readiness behavior;
- stateful official stdio process integration;
- standalone OAuth commissioning;
- approved private-repository read;
- explicit local out-of-scope rejection;
- shared `kis-mcp` runtime mount and `github_*` namespace;
- provider-specific tests and operations documentation.

The change does not modify Work policy, Desktop Commander enforcement, Discover, Skills, Supabase, shared runtime composition, or tunnel configuration.

## Upstream release evidence

Official source:

```text
https://github.com/github/github-mcp-server
```

Pinned release and commit:

```text
v1.8.0
ca8ab52dcc45b86fae190398178fd22edb7b1362
```

The installer resolved the exact release tag through the GitHub REST API, required stable immutable release metadata, resolved the tag to the configured commit, selected `github-mcp-server_Windows_x86_64.zip`, and verified its published digest.

Observed artifact evidence:

```text
published/archive SHA-256: C91ECA7FFD5492C2B273DFCC8747D4B54AFDDCDE342704572A6917C73757F608
installed binary SHA-256:   E8CF444BC58DD3A47938504D4D85E338D76BF558AF463D252CBC554CCAC4C256
installation path:          C:\Projects\.kis-mcp\github-mcp\github-mcp-server.exe
```

The installation workspace was moved into recoverable quarantine. No permanent-delete operation was used.

## TDD evidence

Initial and staged red tests established the following missing behavior before implementation:

- schema version 2, release tag, OAuth mode, and PAT-conflict configuration;
- no PAT forwarding to the official process;
- local readiness separated from authenticated state;
- immutable release and published digest installer structure;
- interactive commissioning module and PowerShell launcher;
- shared-runtime mount and namespaced tool verification;
- explicit scope-error evidence rather than treating arbitrary failures as containment.

The final focused suite reports:

```text
37 GitHub provider tests passed
```

The suite includes a regression ensuring unrelated network/upstream failures cannot be mistaken for `GITHUB_REPOSITORY_SCOPE` evidence.

## Installer verification

Command:

```powershell
pwsh -NoProfile -File .\scripts\install-github-mcp.ps1
```

Result: exit code `0`.

Verified:

- exact release `v1.8.0`;
- exact commit `ca8ab52dcc45b86fae190398178fd22edb7b1362`;
- immutable stable release;
- one Windows x86-64 ZIP asset;
- published SHA-256 equals downloaded archive SHA-256;
- one extracted `github-mcp-server.exe`;
- installation beneath `C:\Projects`;
- recoverable backup path supported;
- no credentials printed or persisted.

## Standalone OAuth commissioning

Command:

```powershell
pwsh -NoProfile -File .\scripts\auth-github-mcp.ps1
```

Result: exit code `0`.

The official provider reported browser authorization opened and GitHub authorization completed. The commissioning report returned:

```json
{
  "approved_repository": "nielpieterse0/kis-mcp",
  "authentication": true,
  "private_repository_read": true,
  "rejected_repository": "github/github-mcp-server",
  "repository_scope": true,
  "surface": true
}
```

No write mutation was performed.

## Shared-runtime live smoke

Command:

```powershell
pwsh -NoProfile -File .\scripts\smoke-github-mcp.ps1 -RequireLive
```

Result: exit code `0`.

Observed report:

```text
release_tag:                  v1.8.0
source_revision:              ca8ab52dcc45b86fae190398178fd22edb7b1362
auth_mode:                    oauth
executable_present:           True
pat_override_present:         False
focused_tests:                passed
live_ready:                   True
live_mounted:                 True
live_surface:                 True
live_authentication:          True
live_private_repository_read: True
live_repository_scope:        True
```

The live path built the normal shared server, verified `kis_provider_status`, and exercised `github_get_me` and `github_get_file_contents` through the mounted namespace. The rejected repository produced explicit `GITHUB_REPOSITORY_SCOPE` evidence.

Expected non-blocking stderr:

- Desktop Commander emits string-form logging notifications that the current FastMCP notification validator warns about.
- The expected rejected `github_get_file_contents` call is logged as an error by FastMCP before commissioning classifies the explicit scope marker.

Neither warning changed the smoke exit code or result booleans.

## Full repository verification

Command:

```powershell
pwsh -NoProfile -File .\scripts\verify.ps1
```

Final result: exit code `0`.

Verified checks:

- canonical configuration and exact HR-001, HR-002, and HR-003 rule set;
- locked external Python interpreter and dependencies;
- 67 Python files passed syntax validation;
- 12 change-governance claims passed;
- complete pytest suite passed with two expected skips;
- final repository verification returned `ok: true`.

The final run was performed after the implementation and closeout documentation were complete.

## Governance repair

The merged `008-github-mcp-provider` claim remained incorrectly marked `active`, creating a real overlap with its successor Slice B. Slice 018 explicitly owns the one-line claim repair and changes its status to `closed`. This restored normal repository claim validation without weakening the validator or changing unrelated active claims.

## Credential handling

Verified properties:

- repository JSON contains no token, authorization code, OAuth state, client secret, or private key;
- `GITHUB_PERSONAL_ACCESS_TOKEN` is treated only as a conflicting override;
- KIS does not forward the PAT environment variable to the official process;
- live scripts refuse commissioning while the PAT override is present;
- OAuth tokens remain inside the official provider process and are not reported by health or smoke output;
- restarting the provider normally requires interactive authorization again.

## Residual limitations

- OAuth is process-lifetime and requires operator interaction after provider restart.
- The official OAuth scope request is broad because the configured toolset is `all`; local repository middleware restricts explicit repository targets, but GitHub-side least-privilege configuration remains limited by the official built-in OAuth application.
- Desktop Commander string-form notification warnings are pre-existing shared-runtime noise and are outside this Slice B boundary.
