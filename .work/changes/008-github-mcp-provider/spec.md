# Change Specification: GitHub MCP Provider Integration

- **Change ID**: `008-github-mcp-provider`
- **Status**: Approved for implementation by operator request
- **Risk Profile**: rigorous
- **Development level**: Complex — provider, authentication, external connector, authorization scope, and operational recovery boundaries

## Outcome

Integrate the official `github/github-mcp-server` as an isolated provider module that can expose its standard read/write GitHub tool surface through a dedicated MCP endpoint, authenticate without storing credentials in the repository, enforce the approved private-repository boundary, report health/readiness, and remain independent of Discover and the Desktop Commander Work boundary.

## Authority and scope

- Authoritative sources:
  - `AGENTS.md`
  - `docs/TRUST-MODEL.md`
  - `SPEC.md`
  - `docs/PLATFORM-CONCEPT.md`, especially `ProviderRegistry` and external provider strategy
  - official `github/github-mcp-server` repository at source revision `3778a41476e31a072430cfee7c5d31c5f72def60`
- Owned paths: see `scope.json`.
- Shared paths: none.
- Excluded paths: all Discover internals, remote commissioning files, `settings/kis-mcp.settings.json`, `src/kis_mcp/config.py`, and `src/kis_mcp/server.py`.
- Dependencies: none.
- Integration owner: none; the module exposes a narrow future composition seam without editing the active composition roots.

## Selected design

Use the official local GitHub MCP server as a separately launched stdio provider. A dedicated JSON document defines the authoritative source revision, executable location, toolsets, token environment variable, approved repositories, and repository-scope rules. A small provider registry records the provider descriptor and builder. A standalone `python -m kis_mcp.providers.github` endpoint proxies the official provider and adds health/readiness plus repository-scope middleware.

This provider is an approved external connector boundary, not a Desktop Commander Work invocation. It therefore does not pass through `ThreeRuleMiddleware`; HR-001 through HR-003 remain unchanged. Repository scoping is connector authorization, not a fourth Work policy rule.

### Alternatives rejected

1. **Hosted remote GitHub MCP endpoint** — rejected for this slice because it adds remote transport/OAuth coupling to the concurrently active ChatGPT commissioning work.
2. **Docker image launched at runtime** — rejected because runtime image pulls are non-deterministic external bootstrap and complicate offline readiness.
3. **Direct GitHub REST reimplementation** — rejected because the project must orchestrate the official provider rather than duplicate its tool surface.

## Requirements

- **REQ-001 — Official provider**: launch only the configured official GitHub MCP server executable and record the authoritative repository and pinned source revision in JSON.
- **REQ-002 — No secrets in repository**: obtain authentication only from a configured environment-variable name; never serialize, log, return, or commit token values.
- **REQ-003 — Tool surface**: request the configured official toolsets, defaulting to `all`, without maintaining a custom allowlist of GitHub tool names.
- **REQ-004 — Repository identity**: normalize repository identifiers from `owner/repo` strings and supported GitHub URLs.
- **REQ-005 — Approved repository scope**: permit repository-bound calls only when every explicit repository target is configured; require explicit `repo:owner/name` qualifiers for repository search queries; allow only configured identity-only unscoped tools.
- **REQ-006 — Read/write parity**: apply the same repository boundary to read and write calls without removing write tools from the provider catalogue.
- **REQ-007 — Provider registry**: register immutable provider metadata and a builder under a unique provider ID.
- **REQ-008 — Health/readiness**: report executable presence, token presence as a boolean, source revision, requested toolsets, approved repositories, and readiness without exposing secrets.
- **REQ-009 — Bootstrap**: provide an operator-supervised installation script that copies a pre-acquired official executable into `C:\Projects\.kis-mcp\github-mcp`, verifies SHA-256, and never downloads implicitly.
- **REQ-010 — Smoke testing**: provide a bounded script that starts the provider endpoint and validates configuration/readiness; live GitHub access remains conditional on an operator-provided scoped token and official binary.
- **REQ-011 — Independence**: do not modify or import Discover internals, Work policy, quarantine, Desktop Commander adapter, remote tunnel commissioning, or the active main server composition.
- **REQ-012 — Contracts**: publish a JSON Schema for provider settings and test exact-key validation, normalization, scope enforcement, registry behavior, launch construction, health redaction, and architecture boundaries.

## Acceptance

1. **Given** valid provider JSON, an existing executable, and the configured token environment variable, **when** the provider server is built, **then** it proxies the official stdio server with `stdio --toolsets=all` and repository-scope middleware.
2. **Given** a tool call targeting `NielPieterse0/kis-mcp`, **when** scope middleware evaluates it, **then** the call is forwarded unchanged.
3. **Given** a call targeting another repository or an unqualified repository search, **when** scope middleware evaluates it, **then** it fails with a corrective `GITHUB_REPOSITORY_SCOPE` error.
4. **Given** a health request, **when** no token is configured, **then** the response reports `token_present=false` and never includes token material.
5. **Given** provider settings containing unknown keys, secrets, an unapproved source, invalid repository IDs, paths outside `C:\Projects`, or empty toolsets, **when** settings load, **then** loading fails structurally.
6. **Given** the final branch, **when** focused tests and `scripts/verify.ps1` run, **then** all applicable checks pass and no excluded path changed.

## Risks and recovery

- Risk: a token with broader GitHub resource access could exceed the configured repository intent through provider tools with no repository argument.
  - Mitigation: require fine-grained token/App installation limited to the approved repository, permit only a minimal configured set of identity-only unscoped tools, and reject unqualified repository searches.
- Risk: upstream tool schemas change.
  - Mitigation: avoid tool-name allowlists, inspect common repository argument forms generically, pin the source revision, and require a live smoke rerun on provider upgrades.
- Risk: the binary is replaced with a different executable.
  - Mitigation: operator installation requires an expected SHA-256 and records no secret or downloaded artifact in the repository.
- Recovery: stop the standalone provider endpoint, remove its ChatGPT connector configuration, and restore the previous binary from operator-controlled storage. No database or persistent schema migration exists.

## Out of scope

- Mounting the provider into `src/kis_mcp/server.py` while Discover and remote commissioning own shared composition paths.
- OAuth browser flow, GitHub App creation, PAT creation, or secret storage.
- Downloading or vendoring the GitHub MCP server in the repository.
- Discover consumption or normalization of GitHub evidence.
- GitHub Enterprise hosts.
- Changing HR-001, HR-002, HR-003, or `policy/kis-mcp.policy.json`.
