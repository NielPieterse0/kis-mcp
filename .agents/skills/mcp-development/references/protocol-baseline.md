# MCP Protocol Baseline

## Load condition

Read this reference when the task depends on a protocol version, capability,
transport, authorization rule, or feature introduced in a recent MCP revision.

## Source hierarchy

Use primary sources in this order:

1. `https://github.com/modelcontextprotocol/modelcontextprotocol`
2. The matching versioned specification/schema in that repository.
3. Official MCP SDK repositories for implementation-specific APIs.
4. Official extension repositories for behavior outside core MCP.
5. Host documentation for host-specific behavior.

Do not use a host guide or SDK convenience API to redefine the protocol.

## Verified baseline — 2026-08-08

At this verification date:

- MCP `2025-11-25` is the latest stable core specification release.
- The repository also contains a `2026-07-28` release candidate/draft. It is not
  the stable baseline and may change before finalization.
- The 2025-11-25 schema declares `LATEST_PROTOCOL_VERSION = "2025-11-25"`.

Before relying on these facts in a future task, re-check the official repository
because the stable revision may have changed.

## 2025-11-25 capabilities worth checking explicitly

The stable revision includes or clarifies:

- tools, resources, prompts, completions, logging, roots, sampling, and
  elicitation capability negotiation;
- URL-mode elicitation in addition to form-mode elicitation;
- tool use within sampling when negotiated;
- experimental task-based durable/deferred requests;
- JSON Schema 2020-12 as the default schema dialect;
- improved OAuth discovery/registration and incremental scope guidance;
- clearer treatment of tool input-validation failures as tool execution errors;
- Streamable HTTP origin validation guidance.

Do not infer client support merely because the protocol defines a capability.
Check negotiated capabilities and the target SDK/client version.

## Primitive ownership

Use the protocol control model:

- prompts are primarily user-controlled;
- resources are primarily application-controlled;
- tools are primarily model-controlled.

This is a design model, not an authorization mechanism.

## Version negotiation

Never hard-code the newest repository revision as universally supported.
Initialization negotiates the protocol version between client and server. Keep
feature usage within the negotiated revision and advertised capabilities.

When a project supports multiple revisions:

1. identify the minimum supported revision;
2. identify features that require later revisions;
3. guard those features by negotiated version/capability;
4. keep a fallback or return a precise unsupported-feature result.

## Transport rules

For current mainstream MCP implementations:

- use stdio for local process transport;
- use Streamable HTTP for remote HTTP transport;
- follow the selected revision's framing, session, origin, resumability, and
  request/response requirements rather than copying legacy SSE examples.

Keep protocol transport separate from deployment topology. A local server may
still be exposed through a supervised tunnel; a remote server may still use
private networking.

## Authorization boundary

The MCP authorization specification applies to HTTP-based transports when
implemented. Stdio integrations should obtain credentials through their local
execution environment rather than implementing the HTTP authorization flow.

Authorization is not synonymous with tool confirmation. A host may still ask a
user to confirm a consequential action even after the server has authorized the
request.

## Stability rule

When a draft or RC contains a useful feature:

- label it draft/RC;
- do not require it for a stable-compatible implementation;
- check SDK/client support separately;
- isolate it behind a capability/version boundary;
- avoid making compatibility claims beyond tested evidence.
