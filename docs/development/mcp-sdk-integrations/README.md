# MCP SDK Integrations

Change `044-mcp-sdk-integrations` adds five exact-revision integration packages to the existing Tools and Providers foundations. The implementation is intentionally installation-free: no runtime builder downloads packages, starts a process, performs authentication, calls a remote service, or reads a credential value.

## Pinned sources

| Module | Classification | Upstream pin | Package pin |
|---|---|---|---|
| MCP Spec | Tool: local read-only plugin metadata | `modelcontextprotocol/modelcontextprotocol@5c4f1768b97198a149d7db05f5026b30c6a3cb12`, `plugins/mcp-spec` | Not an MCP server package |
| Fetch | Tool: approved-external-service MCP adapter | `modelcontextprotocol/servers@76d64c822f5125032f89eb71dbdb94e42b434821`, `src/fetch` | `mcp-server-fetch==0.6.3` |
| Everything | Tool: local-process protocol test adapter | `modelcontextprotocol/servers@76d64c822f5125032f89eb71dbdb94e42b434821`, `src/everything` | `@modelcontextprotocol/server-everything==2.0.0` |
| Python SDK | Staged platform-internal library metadata; runtime provider disabled | `modelcontextprotocol/python-sdk@a4f4ccd091138771535e17191123f20b30fda68e` | locked local distribution `mcp==1.29.0` |
| GitLab | Provider: approved external connector | archived `modelcontextprotocol/servers-archived@9be4674d1ddf8c469e6461a27a337eeb65f76c2e`, `src/gitlab` | `@modelcontextprotocol/server-gitlab==0.6.2` |

## Runtime behavior

Each package owns immutable JSON settings, strict loading, readiness, descriptor construction, and an explicit builder.

- `mcp_spec` returns pinned source metadata and an optional local plugin path. It is not represented as an MCP server or SDK.
- `fetch` returns a fixed Python stdio command only. Its default configuration is disabled because its useful operation requires external network access and is not a Work backend.
- `everything` returns a fixed local Node entry-point command only. It is marked as protocol-test tooling, not a production data source.
- `python_sdk` is checked in with `enabled=false`. Its descriptor remains available for explicit development/tests, but it is not registered in the platform provider registry or mounted as a runtime provider. When a test explicitly enables it, readiness verifies the pinned local `mcp` distribution and the builder imports the module only when called.
- `gitlab` returns a fixed local Node entry-point command and environment-variable names only. It records that the upstream is archived and that live authentication is unverified.

`StdioMcpCommand` has no execution method. It rejects `npx`, `uvx`, `-y`, `--yes`, `@latest`, duplicate arguments, duplicate environment references, and malformed environment-variable names.

## Security and trust boundaries

The implementation preserves the repository's three-rule model:

- HR-001: all configured managed paths remain beneath `C:\Projects`, except the pre-existing local Node executable path.
- HR-002: no Work capability receives external network access. Fetch stays disabled for Work; GitLab remains an explicit external connector candidate.
- HR-003: this change does not delete artifacts. Temporary generated test state is recoverably quarantined.

GitLab settings contain only `GITLAB_API_URL` and `GITLAB_PERSONAL_ACCESS_TOKEN` reference names. They cannot contain a token field because strict settings loading and JSON schema reject unknown keys.

## Installation and commissioning

No requested Tool or Provider package is installed by this change. Future supervised installation must place packages in their configured managed state paths, keep exact versions, and update JSON settings only after operator approval.

Readiness meanings:

- `disabled`: integration is present but intentionally not commissioned.
- `unavailable`: a configured local executable, entry point, or distribution is absent.
- `degraded`: the local package version differs, required GitLab environment references are absent, or the integration cannot be safely exposed at its requested boundary.
- `ready`: local artifacts match the pin; for GitLab this still does not claim successful remote authentication.

## Python SDK lifecycle decision

The Python SDK entry is intentionally retained as staged platform-library metadata and remains disabled. It is not an MCP server, its builder returns a Python module rather than a `FastMCP` server, and the current platform registry does not register it. Runtime composition therefore must not imply that `mcp-python-sdk` is a mounted provider. Re-enabling it requires a separate approved design that defines an actual runtime-provider contract rather than mounting a library module as if it were an MCP server.

The other change-044 integrations retain their existing lifecycle classifications; this decision does not widen or compose Fetch, Everything, or GitLab.

## Verification

The repository tests cover:

- exact source and package pins;
- strict settings and JSON Schema validation;
- command acquisition rejection and deterministic serialization;
- disabled integrations avoiding readiness probes;
- Fetch external-network-only status;
- Everything fixed local entry point;
- Python SDK missing/mismatch/ready states and explicit import behavior;
- GitLab archived status, environment-reference readiness, and absence of secret values.
