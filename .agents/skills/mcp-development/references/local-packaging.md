# Local MCP Packaging

## Load condition

Read this reference when an MCP server must run locally and be distributed as a
host-installable package, including MCPB.

## Boundary

Local packaging is not part of the core MCP protocol. Keep the portable stdio
server separate from host-specific bundle manifests, installers, signing,
runtime embedding, and configuration UX.

MCPB is an Anthropic-origin local packaging format. Do not present MCPB as a
ChatGPT distribution mechanism or as a requirement for an ordinary local MCP
server. Use it only when the target host explicitly supports or requires it.

## Preferred architecture

```text
portable MCP server
    |
    +-- stdio transport
    +-- tools/resources/prompts
    +-- server security + auth
    |
    +-- optional packaging adapter
           +-- host manifest
           +-- bundled runtime/dependencies
           +-- install-time configuration
           +-- icon/assets
           +-- signing/distribution metadata
```

The server should remain runnable and testable without the package wrapper.

## When packaging is justified

Use a local bundle when the server genuinely needs machine-local access such as:

- filesystem or local project state;
- a desktop application or OS API;
- localhost-only services;
- local hardware;
- a runtime that end users should not need to install separately.

If the server only wraps a cloud API, a remote Streamable HTTP server is usually
simpler and easier to update.

## Security

A package manifest is not a sandbox unless the target host explicitly documents
one. Assume the local server process has the privileges granted by the host/OS.

Therefore:

- canonicalize and constrain filesystem paths;
- use client roots where supported and appropriate;
- validate every process spawn and executable target;
- scope credentials to the server process;
- keep secrets out of manifests and bundle assets unless the host provides a
  documented secure secret mechanism;
- avoid runtime downloads during ordinary startup;
- pin and verify bundled dependencies;
- test on a clean machine without the developer toolchain.

## MCPB-specific guidance

When MCPB is the selected target:

- verify the current official MCPB repository/schema before creating a manifest;
- keep `manifest.json` declarative and minimal;
- make the launch command explicitly point at the bundled server entry point;
- map install-time user configuration to explicit environment values consumed
  by the server;
- bundle all required runtime dependencies;
- validate and pack using the current MCPB tooling;
- sign only when the distribution workflow requires it and the operator has the
  appropriate signing authority;
- test installation and launch on each claimed target platform.

Do not infer current schema fields from an old example. MCPB is versioned and
host-specific.

## ChatGPT boundary

For ChatGPT, prefer the current supported MCP/App connection model documented by
OpenAI. A local server may need an approved bridge or tunnel depending on the
product surface, but that does not make MCPB part of the ChatGPT protocol.

Keep these concerns distinct:

- MCP wire protocol;
- local process lifecycle;
- remote reachability/tunneling;
- ChatGPT app metadata/UI;
- third-party packaging formats.

## Validation

Before claiming a local package is complete:

- run the server directly over stdio;
- initialize and call representative operations with an MCP client/Inspector;
- validate the package manifest against its current schema;
- verify the package contains its runtime/dependencies;
- install it in the target host or a clean test environment;
- verify filesystem and credential boundaries;
- confirm removal/upgrade behavior does not destroy user data.
