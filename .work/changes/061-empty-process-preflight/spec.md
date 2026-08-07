# Change 061 — Startup and provider-auth lifecycle repair

## Approved outcome

Repair the startup path as one coherent lifecycle: a clean selected-instance start must accept zero stale processes; GitHub MCP must have one upstream subprocess for one running KIS runtime; successful startup OAuth must become current provider/capability readiness; provider tool discovery must remain progressive without a construction-time GitHub process; and supervised authentication must not consume the tunnel readiness budget or hide device fallback output.

## Requirements

1. `Get-KisMcpRootProcessIds` accepts an empty process collection and returns no roots under production terminating-error semantics.
2. Startup tests treat PowerShell non-terminating errors as failures so stderr-only binder failures cannot produce a false green.
3. GitHub's `PersistentClientProxyProvider` owns one connected client for its complete mounted-server lifespan. `get_me` and initial upstream tool discovery happen inside that connection and nested calls do not disconnect it.
4. Aggregate gateway component discovery must not connect the upstream GitHub MCP process before the persistent provider lifespan starts. Existing discovery behavior for other mounted providers must remain intact. No hard-coded catalogue of the full GitHub tool set is permitted.
5. The provider-neutral descriptor/runtime path may publish a runtime tool snapshot after provider startup. Capability search and generic dispatch may use that current snapshot to expose long-tail provider operations progressively.
6. GitHub readiness must distinguish pre-start authentication-required state from a current runtime whose startup `get_me` succeeded. Provider status and capability eligibility must use current runtime evidence rather than a permanently frozen construction-time auth snapshot.
7. Direct exposure remains bounded. Newly discovered long-tail provider tools remain discoverable/dispatchable through the capability control surface; they are not all promoted to the direct tool list.
8. The human-supervised server/OAuth phase has a separate bounded timeout from machine/tunnel readiness. The machine/tunnel deadline starts after the server/OAuth phase completes.
9. Server stderr remains retained as startup evidence and is also surfaced live in the visible launcher so browser/device-code guidance is usable while authentication is pending.
10. HR-001 through HR-003, repository routing, PAT exclusion, peer-instance isolation, recoverable deletion behavior, and non-GitHub provider discovery remain unchanged.

## Design

### Startup preflight

Keep the existing root-selection algorithm. Change only its parameter contract to permit an empty collection, and harden the test helper with `$ErrorActionPreference='Stop'` so the production binder semantics are exercised.

### Persistent provider lifecycle and progressive discovery

Extend the provider-neutral client lifecycle with two small state objects: startup state (`idle|starting|ready|failed|stopped`) and a runtime tool snapshot. `PersistentClientProxyProvider.lifespan()` enters the client once, performs the optional startup call, lists upstream tools while the outer connection is still held, stores the snapshot, marks startup ready, and only disconnects after parent shutdown.

Before that lifespan is ready, the persistent proxy's upstream `list_tools` path returns an empty component list instead of connecting its client. This lets the gateway retain its existing aggregate component discovery after all providers are mounted, preserving Supabase, Control Center, Desktop Commander, and local runtime surfaces while preventing only the disposable pre-lifespan GitHub subprocess.

`ProviderDescriptor` gains an optional runtime-tool probe without changing the previous positional field order. GitHub registration owns the shared startup/tool-state instances and passes them to the builder and readiness probe. At runtime, capability state augments immutable base contributions with the already captured static runtime surface plus currently published namespaced provider tool snapshots. This preserves progressive discovery without a static GitHub catalogue.

### Runtime readiness

Capability readiness is evaluated from the current effective catalogue/provider probes when search, recommendation, eligibility, or execution occurs. The direct exposure plan is still fixed during gateway construction, while later GitHub long-tail discovery and eligibility observe the current runtime state after `get_me` succeeds.

### Supervised startup

Keep `TimeoutSeconds` as the bounded machine/tunnel timeout. Add a separate bounded server/authentication timeout for `Wait-McpReady`; once the server becomes ready, create a fresh tunnel deadline. Replace deferred-only process stream capture with event-backed draining so server stderr lines are appended to the existing log and echoed to the launcher while waiting. Tunnel output remains logged without unnecessary console noise.

## Verification

- RED/GREEN regression for empty process sets with terminating PowerShell errors.
- Provider lifecycle unit test proving pre-lifespan listing makes no upstream connection and startup discovery plus `get_me` occur with one outer connection and one final disconnect.
- GitHub provider tests proving shared startup state changes readiness after lifespan startup and runtime tools are published without PAT leakage.
- Platform/capability tests proving runtime tools are namespaced, become discoverable/dispatchable after publication, and direct exposure stays bounded.
- Startup script tests proving independent auth/tunnel deadlines and live-retained server stderr.
- Compatibility review proving existing non-GitHub mounted-provider discovery is preserved.
- Canonical repository verification and Windows CI on the exact branch head.

## Out of scope

- Persisting GitHub OAuth tokens across KIS process restarts.
- Changing GitHub OAuth scopes or replacing the official GitHub MCP binary.
- Generalizing Supabase authentication semantics beyond the provider-neutral optional runtime hooks needed here.
- Expanding HR-001 through HR-003.
