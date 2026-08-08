# MCP Apps and ChatGPT

## Load condition

Read this reference when an MCP server needs an interactive UI, embedded widget,
visualization, rich picker, editor, dashboard, or ChatGPT Apps behavior.

## Standards boundary

MCP Apps is an extension to core MCP, maintained in the official
`modelcontextprotocol/ext-apps` repository. As verified on 2026-08-08, its
stable specification revision is `2026-01-26`.

Treat these layers separately:

1. core MCP tool/resource behavior;
2. MCP Apps extension metadata and iframe bridge;
3. ChatGPT-specific Apps SDK metadata and `window.openai` extensions.

Do not require ChatGPT-only APIs for portable MCP Apps unless the user accepts
that compatibility trade-off.

## Use UI only when it materially helps

Prefer plain tool output when text or structured data is sufficient.
Use an MCP App when the interaction benefits from:

- visual/spatial display;
- large searchable selection;
- rich forms or direct manipulation;
- stateful interaction;
- charts, maps, diffs, canvases, previews, or dashboards;
- a focused workflow that is substantially clearer inside a widget.

## Core app pattern

An MCP App is still an MCP server. The common pattern is:

1. register a tool;
2. register a `ui://` resource containing the View;
3. associate the tool with the UI resource using extension metadata;
4. return useful structured/text results from the tool;
5. let the host render the resource in a sandboxed iframe;
6. use the MCP Apps bridge for host/View communication and tool calls.

Keep the tool result useful without the View when practical.

## ChatGPT-specific optimization

Before implementing or changing a ChatGPT app, consult current OpenAI developer
documentation for Apps SDK behavior. Prefer current docs and official examples
over copied historical snippets.

Design rules:

- plan tools before UI;
- keep one clear job per tool;
- use accurate `readOnlyHint`, `destructiveHint`, `idempotentHint`, and
  `openWorldHint` annotations where supported;
- return concise `structuredContent` for model + widget state;
- keep widget-only or bulky data out of model-facing text when the current Apps
  contract provides an appropriate metadata channel;
- version widget resource URIs when caching or compatibility makes that useful;
- configure CSP domains narrowly and explicitly;
- use the standard MCP Apps bridge for portable interactions;
- add `window.openai` only for ChatGPT-specific host capabilities that materially
  improve the requested experience;
- keep local Developer Mode/testing guidance separate from production hosting
  and public submission requirements.

## Bridge and host APIs

Do not assume a wrapper helper is the normative public API. Libraries may expose
convenience methods around the underlying MCP Apps bridge.

For ChatGPT-specific functionality, verify the current documented
`window.openai` surface before use. Typical host-specific needs include:

- component-initiated tool calls;
- follow-up messages;
- external-link opening;
- display-mode requests;
- theme/locale/layout signals;
- tool input/output state;
- widget state;
- file or modal flows.

Names and availability may evolve. Re-check OpenAI docs rather than preserving
stale examples in new code.

## State design

For non-trivial widgets:

- make server state authoritative for durable business state;
- keep purely presentational state in the View;
- use explicit versions/tokens for retry-safe mutations;
- separate data-fetch tools from render tools when it improves reuse;
- avoid re-sending large payloads on every interaction;
- make repeated tool calls idempotent or reject unsafe retries precisely.

## Security

The View runs in a host-controlled sandbox, but the server must still enforce
its own security boundary.

- declare only required CSP connect/resource domains;
- do not rely on iframe isolation as server authorization;
- do not expose secrets in tool results or widget source;
- route privileged operations through server tools with normal authorization;
- validate all component-provided arguments as untrusted input;
- avoid arbitrary frame domains or third-party script origins without a real
  requirement;
- preserve a meaningful non-UI fallback for unsupported hosts when feasible.

## Validation

Validate at three levels:

1. **Server contract** — tool/resource registration and normal MCP calls.
2. **MCP Apps contract** — UI resource metadata, bridge handshake, tool result
   delivery, component-initiated calls, resizing/state behavior, CSP.
3. **ChatGPT host** — Developer Mode connection, widget rendering, current
   `window.openai` features, repeated interactions, mobile/layout behavior when
   relevant.

A successful render in one host does not prove the extension works in all MCP
clients.
