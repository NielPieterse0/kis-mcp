# MCP Authority Receipt

- FastMCP runtime authority: repository dependency `fastmcp==3.4.4` (`pyproject.toml` and `uv.lock`).
- Normative MCP authority: operator-supplied MCP specification/schema revision `2025-11-25` only.
- Explicitly excluded: MCP `2026-07-28` and FastMCP 4.x design/migration assumptions.

## Relevant normative contracts consulted

- `resources/list` returns `ListResourcesResult.resources` containing MCP `Resource` descriptors.
- `resources/templates/list` returns `ListResourceTemplatesResult.resourceTemplates` containing MCP `ResourceTemplate` descriptors.
- `resources/read` accepts a URI string selected by the server and returns `ReadResourceResult.contents` as `TextResourceContents | BlobResourceContents` entries.
- Resource URIs may use any protocol; interpretation is server-owned.
- Text resource contents carry URI, optional MIME type, and text; blob resource contents carry URI, optional MIME type, and base64-encoded binary data at the protocol boundary.

## Design consequence

The historical Skills design is protocol-aligned in shape: canonical entrypoints/supporting files are exposed as read-only resources/templates, and FastMCP 3.4.4 performs the protocol serialization. KIS keeps byte-identity/staleness/path-safety logic inside the Skills catalogue and does not invent a parallel resource transport contract.