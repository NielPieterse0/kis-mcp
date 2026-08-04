# GitHub MCP Provider Verification

## Scope

Verified branch: `change/008-github-mcp-provider`

Verified module boundary:

- `src/kis_mcp/providers/github/**`;
- `src/kis_mcp/provider_registry.py`;
- provider JSON and schema;
- operator install and smoke scripts;
- focused tests and development documentation.

The branch does not modify Discover, the Desktop Commander Work gateway, policy, quarantine, remote tunnel commissioning, or the active main server composition.

## Upstream evidence

The implementation uses the official source identity:

```text
https://github.com/github/github-mcp-server
```

Configured source revision:

```text
3778a41476e31a072430cfee7c5d31c5f72def60
```

The official provider documentation and source at that revision confirm local stdio operation, toolset configuration through `--toolsets`, token-based authentication, and repository tools using explicit `owner` and `repo` inputs.

## TDD evidence

### Initial red

After writing the first provider tests, `scripts/verify.ps1` failed during test collection because these production modules did not exist:

- `kis_mcp.provider_registry`;
- `kis_mcp.providers.github.settings`;
- `kis_mcp.providers.github.scope`;
- `kis_mcp.providers.github.server`.

This established that the tests exercised the new behavior rather than existing implementation.

### Boundary regression red

A later review added tests for:

- `owner` plus `repository_name` identity;
- full `owner/repo` supplied through `repo`;
- stable `GITHUB_REPOSITORY_SCOPE` errors for malformed targets.

The focused suite failed in `scope.py` before the extraction and error-normalization fix, then passed after the minimal change.

### Live commissioning regression red

The staged review found that `-RequireLive` only invoked the executable with `--help`. A script regression test was added requiring the dedicated MCP smoke module and prohibiting the shallow `--help` check. The focused suite failed before the script was updated.

The replacement live smoke now initializes the MCP proxy, verifies the pinned `get_me`, `get_file_contents`, and `create_or_update_file` surface, calls redacted health, authenticates with `get_me`, and reads `README.md` from the approved private repository without printing content or performing a write mutation.

### Green

Command:

```powershell
pwsh -NoProfile -File .\scripts\smoke-github-mcp.ps1
```

Result:

```text
34 tests passed
provider: github-mcp
source_revision: 3778a41476e31a072430cfee7c5d31c5f72def60
executable_present: False
token_present: False
focused_tests: passed
live_required: False
```

The absent executable and token are expected in static verification and are reported without secret material.

## JSON validation

Validated successfully:

```text
settings/providers/github-mcp.provider.json
contracts/providers/github/provider-settings.schema.json
```

Both documents parsed as valid JSON. Tests also verify exact-key loading, bounded schema structure, official source identity, pinned revision shape, path boundary, token indirection, toolsets, repository normalization, duplicate rejection, and unknown-key rejection.

## Full repository verification

Command:

```powershell
pwsh -NoProfile -File .\scripts\verify.ps1
```

Result: exit code `0`.

Verified checks reported:

- canonical configuration and exact HR-001/HR-002/HR-003 rule set;
- locked external Python interpreter;
- pinned FastMCP and pytest dependencies;
- Python syntax for 26 files;
- repository change-governance implementation check;
- complete pytest suite;
- final repository verification result.

## Change-governance status

`change-workflow new` and global `change-workflow validate` remain blocked by a pre-existing repository workflow defect: merged changes `004-live-proxy-commissioning` and `006-provider-state-atomicity` are copied as active records into linked worktrees, producing duplicate change ID, branch, worktree, outcome, and path findings.

This branch used the documented emergency path:

1. create an isolated worktree manually from clean `main`;
2. register `008-github-mcp-provider` locally before implementation;
3. declare exclusive owned and excluded paths;
4. run baseline verification;
5. preserve the governance failure as explicit evidence.

No `008` versus `005`, `007`, or `009` owned-path overlap was identified. The concurrent `009-supabase-mcp-provider` scope explicitly excludes the GitHub provider and central registry paths.

## Review

A dedicated reviewer subagent was not available in this execution environment. A direct whole-change review covered:

- specification and acceptance criteria;
- official-provider launch shape;
- credential handling and output redaction;
- repository identity normalization;
- read/write repository scope symmetry;
- malformed input and corrective errors;
- architecture independence;
- operator bootstrap and recovery;
- tests, documentation, and scope discipline.

Finding resolved during review:

- **Important — unstable scope error and alternate field incompatibility.** `repository_name` with `owner`, a full identity in `repo`, or a malformed explicit repository could produce an incorrect raw `ValueError`. Regression tests were added and extraction now supports the alternate forms while normalizing malformed input to `GITHUB_REPOSITORY_SCOPE`.

No unresolved critical or important code finding remains in the reviewed scope.

## Live verification not performed

The following evidence is intentionally absent:

- official executable installed at `C:\Projects\.kis-mcp\github-mcp\github-mcp-server.exe`;
- operator-provided `GITHUB_PERSONAL_ACCESS_TOKEN`;
- authenticated read and write calls against `NielPieterse0/kis-mcp`;
- ChatGPT tunnel/control-plane composition.

Therefore this branch establishes the provider module and static commissioning path, but does not claim live GitHub MCP readiness. Live commissioning requires an operator-approved official binary, repository-scoped credential, `smoke-github-mcp.ps1 -RequireLive`, and authenticated MCP call evidence.
