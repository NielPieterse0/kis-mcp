# Change Specification: Supabase MCP Provider Integration

- **Change ID**: `009-supabase-mcp-provider`
- **Status**: Approved for implementation by operator request
- **Development level**: Complex — external provider, credentials, project authorization, remote transport, and operational recovery boundaries

## Outcome

Integrate the official hosted Supabase MCP server as an independently executable adapter beneath the shared Provider module. The adapter must proxy the official streamable-HTTP endpoint through a dedicated stdio MCP endpoint, scope the connection to one operator-configured Supabase project, expose the upstream configured read/write tool surface without a custom tool allowlist, keep credentials out of the repository, report redacted provider-specific and provider-neutral readiness, and remain independent of Discover, Desktop Commander Work enforcement, and ChatGPT remote commissioning.

## Authority and upstream evidence

- Repository authority: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, and `docs/PLATFORM-CONCEPT.md`.
- Official MCP Registry entry: `https://github.com/mcp/com.supabase/mcp`.
- Official source repository: `https://github.com/supabase/mcp`.
- Reviewed source revision: `5cda0672702c65fe672280ee4cf306593e643fb6` (2026-07-30).
- Official hosted endpoint: `https://mcp.supabase.com/mcp`.
- Official manual/CI authentication supports `Authorization: Bearer <PAT>` and project scoping through the `project_ref` query parameter.

## Selected design

Use FastMCP 3.4.4 `StreamableHttpTransport` and `create_proxy(ProxyClient(...))` to proxy the official hosted endpoint. Configuration is a strict standalone JSON document. The document stores only provider identity, the reviewed upstream revision, endpoint identity, environment-variable names, project-scoping behavior, read-only mode, optional feature groups, TLS verification, and downstream transport. The actual project reference and access token are supplied at runtime through named environment variables.

The default checked-in configuration is project-scoped and read/write (`read_only=false`). It does not maintain a custom Supabase tool-name allowlist. An empty feature list omits the `features` query parameter so the official server determines its current default feature groups.

This provider is an approved external connector boundary, not a Desktop Commander Work invocation. It does not pass through `ThreeRuleMiddleware`, and it does not change HR-001, HR-002, or HR-003. Project scoping and credential requirements are connector authorization and provider identity controls, not additional Work policy rules.

The shared Provider foundation from PR #9 is authoritative. This adapter uses the canonical `ProviderDescriptor`, `ProviderReadiness`, and `ProviderRegistry` contracts, exposes an explicit `register_provider(registry)` function, and does not modify or auto-populate the provider-neutral core. Platform-wide composition remains a separate integration step.

## Requirements

- **REQ-001 — Official provider identity**: accept only the official hosted endpoint with TLS verification enabled, and record the official repository and reviewed revision in JSON.
- **REQ-002 — Strict JSON configuration**: reject unknown keys, wrong schema versions, malformed URLs, invalid environment-variable names, duplicate/empty features, and unsupported transports.
- **REQ-003 — No secrets in repository**: configuration stores environment-variable names only. Token and project-ref values must never be serialized, logged, returned, or committed.
- **REQ-004 — Project scope**: require a non-empty project reference from the configured environment variable and add it to the upstream URL as `project_ref`.
- **REQ-005 — Read/write parity**: default `read_only` to `false`; when false, omit `read_only` from the URL and expose the official mutating tools. When explicitly configured true, add `read_only=true` without custom tool filtering.
- **REQ-006 — Feature passthrough**: an empty feature list omits the parameter; a configured list is encoded unchanged and does not become a custom tool-name allowlist.
- **REQ-007 — Authentication**: load the PAT from the configured environment variable and pass it only as transport bearer authentication.
- **REQ-008 — Proxy endpoint**: expose a dedicated stdio server named by configuration, proxying the official streamable-HTTP server without Work middleware.
- **REQ-009 — Health/readiness**: report configuration validity, endpoint kind, source revision, project-scoped state, project-ref presence, token presence, read-only mode, features, and readiness without exposing runtime values.
- **REQ-010 — Standalone execution**: support `python -m kis_mcp.providers.supabase` and a non-network `--check` mode that prints redacted readiness JSON.
- **REQ-011 — Smoke script**: provide a bounded PowerShell script that runs `--check`; live upstream listing is optional and only runs when explicitly requested with credentials present.
- **REQ-012 — Contracts and tests**: publish JSON Schema and test strict loading, URL encoding, credential redaction, transport construction, server construction, CLI checking, architecture boundaries, and smoke-script content.
- **REQ-013 — Independence**: do not modify Discover, Work policy, Desktop Commander, quarantine, remote runtime, global settings/config/server, GitHub provider paths, or the provider-neutral core.
- **REQ-014 — Shared Provider conformance**: expose the canonical shared descriptor, provider-neutral redacted readiness probe, and explicit registry function without import-time registration, provider construction, startup, or network access.

## Acceptance

1. Valid settings plus runtime `SUPABASE_PROJECT_REF` and `SUPABASE_ACCESS_TOKEN` produce an upstream URL containing the encoded project reference and a bearer-authenticated `StreamableHttpTransport`.
2. Default configuration omits `read_only` and `features`, preserving the official project-scoped read/write default tool surface.
3. Explicit read-only or features configuration maps only to the corresponding official query parameters.
4. Missing credentials cause readiness to report false and normal server startup to fail with a corrective structural error; `--check` remains non-network and redacted.
5. Health and CLI output never contain the token or project-ref values.
6. Unknown configuration keys, embedded secrets, unsupported external endpoints, and malformed environment-variable names fail before transport construction.
7. Focused tests, scope checks, the non-network smoke command, and `scripts/verify.ps1` pass on the final branch.
8. The shared descriptor declares an approved external connector and `database.manage` capability; provider-neutral health remains redacted; explicit registration adds exactly one Supabase descriptor without building or starting it.

## Risks and recovery

- **Credential authority**: a PAT can inherit broad user privileges. Mitigation: require a dedicated environment variable, project scope in the URL, development/test projects only, and no token persistence.
- **Production data**: upstream documentation warns against production use. Mitigation: document development/test-only operation and require explicit project reference.
- **Upstream schema drift**: remote tools may change. Mitigation: do not hardcode tool names; record reviewed source revision and require smoke verification when upstream behavior changes.
- **Remote outage/auth failure**: the standalone endpoint may be unavailable. Recovery: stop the provider process and remove its connector configuration; no local or remote schema migration is performed by installation.
- **Shared-contract drift**: adapter metadata could diverge from the Provider foundation. Mitigation: use the canonical shared record types directly and cover descriptor, health, registration, and package exports with adapter tests.

## Out of scope

- Creating Supabase projects, PATs, OAuth clients, or browser OAuth sessions.
- Persisting OAuth tokens or credentials.
- Installing or vendoring the Supabase npm package.
- Reimplementing Supabase APIs or tool schemas.
- Connecting to production data.
- Modifying the provider-neutral core or automatically composing adapters into the active platform server.
- Discover normalization of Supabase evidence.
- Changing HR-001, HR-002, HR-003, or `policy/kis-mcp.policy.json`.
