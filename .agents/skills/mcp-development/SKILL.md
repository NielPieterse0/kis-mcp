---
name: mcp-development
description: >
  Use when designing, building, reviewing, testing, packaging, or modernizing a
  Model Context Protocol (MCP) server or integration, including tools,
  resources, prompts, transports, authorization, elicitation, sampling, tasks,
  MCP Apps, ChatGPT widgets, or local MCP packaging. Ground protocol behavior in
  the current official MCP specification and treat host-specific behavior as a
  separate compatibility layer. Do not use for ordinary API integrations that
  do not expose MCP or for generic frontend work unrelated to an MCP App.
---

# MCP Development

## Purpose

Build the smallest interoperable MCP solution that satisfies the user outcome,
uses the protocol primitives correctly, and keeps core MCP behavior separate
from host-specific extensions and packaging.

## Authority and source order

Before making version-sensitive protocol claims or generating implementation
code:

1. Read the governing repository or workspace instructions.
2. Check the current official MCP specification and schema in
   `modelcontextprotocol/modelcontextprotocol`.
3. Prefer the latest stable specification supported by the target SDK/client.
4. Treat release candidates, drafts, extensions, SDK helpers, examples, and host
   documentation as separate evidence, not as core protocol requirements.
5. For ChatGPT-specific Apps behavior, check current OpenAI developer docs.
6. For MCP Apps behavior, check the official `modelcontextprotocol/ext-apps`
   specification and SDK docs.

Never copy a host-specific requirement into the MCP core contract without
source evidence.

## Default workflow

### 1. Classify the requested outcome

Choose the smallest applicable shape:

- **MCP server** — tools/resources/prompts over stdio or Streamable HTTP.
- **MCP App** — an MCP server plus interactive UI resources.
- **Local package** — a local stdio server that must be distributable as a
  host-specific package such as MCPB.
- **Existing implementation review** — inspect and repair protocol, schema,
  security, interoperability, or host-compatibility defects.

If UI is required, also load `references/apps.md`.
If local packaging is required, also load `references/local-packaging.md`.
For version-sensitive protocol decisions, load `references/protocol-baseline.md`.

### 2. Establish implementation constraints

Infer what is already clear and only stop for missing facts that materially
change the architecture. Determine:

- local vs remote execution;
- intended clients/hosts;
- read-only vs mutating operations;
- upstream systems and auth model;
- implementation language/framework;
- expected scale of the operation catalogue;
- whether mid-call user input, long-running work, or embedded UI is required;
- deployment, packaging, and compatibility targets.

Do not force a deployment model from an old example. Select it from the actual
runtime boundary.

### 3. Design the protocol surface before code

Use MCP primitives according to control ownership:

- **Tools** for model-invoked operations.
- **Resources** for application-managed contextual data.
- **Prompts** for user-selected reusable prompt templates.

Add optional capabilities only when the use case requires them:

- elicitation for server-requested user input;
- sampling when the server legitimately needs client-provided model inference;
- roots when the client should declare filesystem boundaries;
- tasks when durable/deferred execution is supported by both sides;
- logging, progress, cancellation, completions, and subscriptions when useful.

Always gate optional behavior on negotiated capabilities. Design a meaningful
fallback when a client may not support the feature.

### 4. Design tools for model selection

Prefer explicit tools with narrow schemas when the useful surface is small.
For large operation catalogues, prefer progressive discovery such as
search/describe/execute or another bounded catalogue pattern rather than
placing hundreds of schemas in the default context.

For every tool:

- give it one clear job;
- use a concise action-oriented name;
- describe when to call it and what result it returns;
- make required inputs explicit and machine-friendly;
- use bounded enums, limits, and defaults where meaningful;
- report tool execution/input failures in a form the model can correct;
- set annotations accurately and never use them as an authorization boundary;
- distinguish read-only, idempotent, destructive, and open-world behavior.

Do not make a generic executor weaker than the original operation contracts.
If using search/execute, preserve original schemas and authorization checks at
execution time.

### 5. Select transport and authorization

Use **stdio** for local process-based integrations and **Streamable HTTP** for
remote servers unless the target environment establishes another supported
transport.

For HTTP authorization, follow the current MCP authorization specification and
its OAuth-based discovery/registration requirements. For stdio, do not invent
an HTTP OAuth flow; provide credentials through the host/process environment or
another local mechanism appropriate to the target runtime.

Keep protocol authorization separate from application-level permissions and
from user-confirmation UX.

### 6. Implement with an appropriate SDK

Prefer an official MCP SDK when it fits the language and feature set. FastMCP is
reasonable for Python when the project already uses it or its abstractions are
materially simpler, but validate wire behavior against the MCP specification
rather than assuming framework helpers are normative.

Follow the existing repository stack when modifying an established project.
Do not rewrite a working server into another language or framework without a
material reason.

### 7. Add MCP Apps only when UI adds value

Load `references/apps.md` before implementing interactive UI.

Do not add a widget for data that plain structured/text output represents well.
Use an app when the user needs a visual display, rich interaction, large
picker, editor, canvas, dashboard, or stateful UI that materially improves the
workflow.

Keep the tool useful without the UI wherever practical so non-App hosts degrade
gracefully.

### 8. Treat local packaging as host-specific

Load `references/local-packaging.md` when the server must be packaged for local
installation.

MCPB and similar bundles are not core MCP. Keep the stdio server itself
portable and isolate packaging manifests, runtime bundling, host configuration,
and signing from protocol logic.

### 9. Apply security at the real boundary

MCP metadata is descriptive, not a sandbox. Enforce security in the server,
host, runtime, or upstream system that owns the effect.

At minimum:

- validate and canonicalize filesystem paths;
- constrain credentials and secrets to the intended process/service;
- verify authorization on every protected action;
- avoid token passthrough to unintended upstreams;
- validate origins for HTTP transports where required;
- bound payloads, pagination, retries, concurrency, and output size;
- make mutating operations explicit and retry-safe where possible;
- treat tool/resource content as untrusted data;
- preserve user control for sensitive or consequential actions.

Do not claim the MCP protocol itself provides a local-process sandbox.

### 10. Validate interoperability, not just compilation

Use the target project's normal verification first, then exercise the MCP
surface end-to-end.

Verify as applicable:

- initialize/version negotiation;
- advertised client/server capabilities;
- tools/list and representative tools/call behavior;
- resources/list/read and prompts/list/get when present;
- structured content and error/result shapes;
- pagination and list-changed notifications;
- cancellation/progress behavior;
- auth discovery and protected calls for HTTP servers;
- capability-gated elicitation/sampling/tasks;
- app resource rendering and fallback when UI is present;
- stdio framing and stderr logging for local servers;
- repeated/idempotent calls and failure recovery.

Use MCP Inspector or an equivalent protocol client when available, but do not
treat one host passing as proof of cross-host compatibility.

## ChatGPT optimization

When ChatGPT is a target host:

- keep tool descriptions concise and intent-oriented;
- keep the directly exposed schema surface small enough for reliable selection;
- preserve a discoverable long tail when the domain is large;
- use structured content deliberately instead of returning large text blobs;
- separate MCP-standard behavior from OpenAI-specific Apps metadata/APIs;
- use current OpenAI docs for Developer Mode, Apps SDK metadata, CSP, widget
  state, file flows, submission, and `window.openai` behavior;
- prefer MCP Apps bridge semantics where portability matters, adding
  ChatGPT-specific extensions only when they improve the target experience.

## Gotchas

- The newest repository branch or RC is not automatically the stable protocol.
- SDK support may lag the newest specification; negotiate versions rather than
  assuming both ends implement the same revision.
- MCP Apps is an extension, not a core MCP primitive.
- MCPB is packaging, not a transport or authorization model.
- Tool annotations do not enforce permission or safety.
- A large provider should not expose hundreds of equal-weight tool schemas when
  progressive discovery can retain functionality with less context cost.
- Host examples may contain compatibility helpers that are not normative APIs.
- UI CSP, iframe behavior, and host globals are host/extension concerns; verify
  them against current docs before shipping.

## Completion criteria

The task is complete only when:

- the deployment shape and target hosts are explicit;
- core MCP behavior matches an identified official specification revision;
- optional features are capability-gated;
- tools/resources/prompts have clear ownership and schemas;
- auth and effect enforcement exist at the correct boundary;
- host-specific extensions are isolated from the portable core;
- version-sensitive claims were checked against current primary sources;
- applicable protocol and repository verification has run;
- unverified compatibility, deployment, or live-auth claims are stated as such.
