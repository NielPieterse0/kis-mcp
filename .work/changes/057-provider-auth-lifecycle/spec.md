# Change 057 — Provider authentication lifecycle

## Approved outcome

Keep authenticated upstream MCP clients alive for one complete `kis-op` runtime, while keeping provider authentication independent from repository and GitHub Project routing.

## Root cause

The GitHub provider mounts FastMCP `StatefulProxyClient.new_stateful`. FastMCP invokes that factory for downstream sessions, so a local GitHub MCP subprocess is created and closed with each downstream session. The official GitHub MCP OAuth credential is process-memory state; closing the subprocess discards it and causes the next tool call to authenticate again.

## Required behavior

1. A reusable provider-neutral lifecycle component owns one FastMCP `Client` for the parent server lifespan.
2. Nested proxy operations reuse that connected client and do not close its subprocess until parent shutdown.
3. GitHub supplies a provider-specific startup bootstrap that calls `get_me` once per runtime to trigger OAuth.
4. Restarting the runtime creates one new client and therefore one expected OAuth login.
5. Provider settings contain provider identity, pinned executable, OAuth mode, and toolsets only; repository and GitHub Project bindings are not authentication configuration.
6. Repository-local `settings/kis-repository.settings.json` declares the GitHub repository and `gh_projects` bindings.
7. GitHub repository calls require explicit repository identity and project operations are restricted to bindings from the selected repository settings.
8. Repository settings validate the declared GitHub repository against the local `origin` remote when that remote is available.
9. A mutable repository-settings source may switch selected repository context without rebuilding or reconnecting the authenticated provider client.
10. PAT override remains absent from the provider process environment and is reported as a configuration conflict if present in the parent environment.

## Modularity decision

FACT: GitHub provider construction currently combines upstream process/session lifecycle, OAuth bootstrap expectations, provider health, and repository/project authorization.

INFER: Those responsibilities have different change reasons. Process/session reuse is shared by local and remote MCP providers; GitHub OAuth bootstrap and GitHub routing are provider-specific.

REC: Add a small provider-neutral persistent client proxy provider. Keep startup bootstrap injectable. Move repository and Project bindings into a repository module and leave GitHub argument authorization in the GitHub adapter.

RISK: Do not create a universal credential store, token broker, or cross-provider auth abstraction in this slice. Supabase and future Cloudflare adapters may adopt the lifecycle component separately when their session semantics are verified.

## Verification

- lifecycle unit tests prove one outer connect, nested proxy reuse, one startup bootstrap, and one shutdown;
- GitHub server tests prove a plain shared `Client` and persistent proxy provider replace `StatefulProxyClient`;
- repository settings tests cover strict JSON, remote agreement, mismatch failure, worktree gitdir resolution, and `gh_projects` validation;
- routing tests prove repository and project authorization changes when the selected repository settings source changes without replacing the provider client;
- provider settings tests prove repository/project keys are rejected and PAT is never forwarded;
- full repository verification and Windows CI pass at the exact PR head.
