# Change Specification: MCP SDK Integrations

- **Change ID**: `044-mcp-sdk-integrations`
- **Status**: Approved for implementation by the operator's explicit `GO` directive
- **Development level**: Complex
- **Base**: rebased onto `main` at `0d49cf6`

## Outcome

Add five pinned, modular integrations without installing packages during development and without overlapping active central-runtime changes:

1. Tools: MCP Spec plugin metadata, Fetch MCP server, Everything MCP test server.
2. Providers: official MCP Python SDK library provider, archived GitLab MCP connector provider.

The slice delivers descriptors, settings models/loaders, readiness checks, explicit builders, JSON schemas/settings, and focused tests. It does not mount the integrations into the public gateway while active changes `040-context7-serena-adapters` and `043-control-center-ui-integration` own the central Tools/Providers composition files.

## Authority and upstream pins

- MCP Spec plugin: `modelcontextprotocol/modelcontextprotocol@5c4f1768b97198a149d7db05f5026b30c6a3cb12`, path `plugins/mcp-spec`.
- Fetch server: `modelcontextprotocol/servers@76d64c822f5125032f89eb71dbdb94e42b434821`, package `mcp-server-fetch==0.6.3`.
- Everything server: same repository revision, package `@modelcontextprotocol/server-everything==2.0.0`.
- Python SDK: `modelcontextprotocol/python-sdk@a4f4ccd091138771535e17191123f20b30fda68e`, distribution `mcp`.
- GitLab server: archived `modelcontextprotocol/servers-archived@9be4674d1ddf8c469e6461a27a337eeb65f76c2e`, package `@modelcontextprotocol/server-gitlab==0.6.2`.

## Requirements

- **R1 — Modularity**: Each integration has a focused package with immutable settings, descriptor construction, readiness, and explicit build behavior. No integration imports another integration package.
- **R2 — Pinning**: Settings record exact upstream repository, revision, package identity, and package version where applicable. Floating `latest`, `-y`, or runtime package acquisition is forbidden.
- **R3 — No implicit installation**: Readiness probes inspect only configured local executables/modules/paths. Builders construct adapters or metadata handles but never install, update, download, authenticate, or start a remote operation.
- **R4 — HR-002 truthfulness**: Fetch is represented as external-network-only and disabled for Work exposure. GitLab is an approved external connector candidate, not a Work backend. Everything is local protocol test tooling. MCP Spec is source/plugin metadata. Python SDK is a local library provider.
- **R5 — Archived GitLab boundary**: GitLab readiness and descriptor output explicitly report archived upstream status, PAT environment-variable dependency, and unverified authentication. No token value is read or serialized.
- **R6 — Safe command construction**: Stdio command builders use fixed executable/argument arrays from validated JSON settings. They reject acquisition flags and do not invoke shells.
- **R7 — Deterministic contracts**: JSON settings validate with checked-in schemas; descriptors serialize deterministically and redact environment values.
- **R8 — Conflict-free delivery**: Do not edit central runtime files claimed by active changes. Record the deferred public-composition step explicitly.
- **R9 — Verification**: Focused tests, JSON validation, change-workflow check, architecture/import checks, and full `scripts/verify.ps1` pass on the final branch state.

## Design

### Shared stdio command model

`tools/mcp_stdio.py` defines a small immutable `StdioMcpCommand` value object. It validates executable, arguments, environment-variable names, package-acquisition flags, and JSON-safe serialization. It exposes no execution method.

### Tool integrations

- `mcp_spec`: represents the upstream Claude plugin/skill bundle as source metadata and optional local checkout readiness. It is not misrepresented as an MCP server or SDK.
- `fetch`: represents the pinned Python MCP server. Its capability is external-network-only; the descriptor is disabled for Work exposure and its builder returns a fixed local stdio command only when a local interpreter/module path is configured.
- `everything`: represents the pinned protocol conformance/test server. Its builder returns a fixed local Node entry-point command; it does not use `npx` acquisition.

### Provider integrations

- `python_sdk`: reports availability/version of the already-installed `mcp` distribution and builds an import handle through an injected importer. It does not alter `pyproject.toml` or `uv.lock` in this slice.
- `gitlab`: represents the archived GitLab MCP connector as an approved-external-connector candidate. Its builder returns a fixed local Node entry-point command and environment-variable names only. Authentication and live GitLab access remain unverified and uncommissioned.

## Acceptance criteria

1. All five descriptors expose exact upstream pins and correct boundary/kind/effect metadata.
2. No builder or readiness probe performs network access, installation, authentication, subprocess execution, or secret reads.
3. Fetch cannot be reported as Work-ready or generally exposed while its only capability requires external network access.
4. GitLab output states that the upstream repository is archived and keeps token values absent from settings/results.
5. Invalid settings, floating versions, acquisition commands, duplicate arguments, and malformed environment-variable names fail structurally.
6. Tests prove explicit construction, readiness states, serialization, and no-install/no-secret behavior.
7. Central registration/mounting remains deferred because active worktrees own those files; the closeout names the follow-on integration point.

## Exclusions

- Package installation, dependency-lock changes, or runtime downloads.
- Public gateway registration or provider-runtime mounting.
- Live network calls, OAuth/PAT commissioning, or credential persistence.
- Changes to `SPEC.md`, `docs/OPERATIONS.md`, policy, Desktop Commander, or active worktree-owned central files.
- Forking or vendoring upstream repositories.

## Recovery

The change creates repository files only. Recovery is ordinary PR revert. No package, credential, generated state, or external service state is changed.
