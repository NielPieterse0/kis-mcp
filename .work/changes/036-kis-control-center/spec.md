# Change Specification: KIS Control Center

- **Change ID**: `036-kis-control-center`
- **Status**: Approved
- **Development level**: Medium
- **Risk Profile**: standard

## Outcome

Add a separate, dependency-free, read-only KIS Control Center MCP App that presents truthful operational status without modifying, wrapping, vendoring, or forking Desktop Commander.

## Authority and scope

- Authoritative sources: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, `policy/kis-mcp.policy.json`.
- Approved design source: the operator-approved recommendation in the current conversation.
- Owned paths: `src/kis_mcp/control_center/**`, `tests/control_center/**`, `settings/control-center.settings.json`, `contracts/control-center/**`, `docs/development/control-center/**`.
- Excluded integration paths: `src/kis_mcp/server.py`, `src/kis_mcp/tools/**`, `SPEC.md`, `docs/OPERATIONS.md`, Desktop Commander installation contents, and policy files.
- Delivery form: a standalone FastMCP MCP App runnable with `python -m kis_mcp.control_center`; later mounting into the main gateway is additive and outside this slice while `server.py` is exclusively claimed by another active change.

## Requirements

- **REQ-001 — Separation**: The implementation SHALL live in a focused `kis_mcp.control_center` package and SHALL NOT modify Desktop Commander or the main gateway integration surface.
- **REQ-002 — MCP App contract**: The server SHALL expose one model-visible `open_kis_control_center` tool linked to one `ui://` resource with MIME type `text/html;profile=mcp-app`.
- **REQ-003 — Read-only snapshot**: The snapshot SHALL report runtime identity, Desktop Commander installation state, current project Git state, the exact three policy rules, configured provider entries, quarantine summary, and truthful verification guidance without performing mutations or network access.
- **REQ-004 — Truthful status**: Configuration SHALL not be presented as authentication, commissioning, live provider connectivity, or successful verification. Unknown states SHALL remain explicit.
- **REQ-005 — Self-contained UI**: The UI SHALL contain no external scripts, styles, images, fonts, frames, or network calls. It SHALL use host-provided theme variables when available and safe local fallbacks otherwise.
- **REQ-006 — Safe rendering**: All runtime-derived text SHALL be HTML-escaped. The renderer SHALL produce deterministic section order and bounded item counts.
- **REQ-007 — JSON configuration**: Control Center settings SHALL be JSON and covered by a JSON Schema.
- **REQ-008 — Standalone operation**: The module SHALL run from the existing source checkout without adding or changing package dependencies or project entry points.
- **REQ-009 — Verification**: Focused tests SHALL prove snapshot behavior, escaping, absence of external resource references, MCP tool/resource metadata, and settings/schema validity. Full repository verification SHALL pass on the final branch state.

## Acceptance

1. **Given** the source checkout, **when** `python -m kis_mcp.control_center` starts, **then** a standalone FastMCP server is available without changing Desktop Commander or the main gateway.
2. **Given** an MCP client, **when** tools and resources are listed, **then** `open_kis_control_center` references `ui://kis-mcp/control-center.html` and that resource uses the MCP App MIME type.
3. **Given** local runtime settings and a project repository, **when** the snapshot is collected, **then** it reports bounded local evidence and labels provider/verification uncertainty explicitly.
4. **Given** hostile text in local status fields, **when** the UI is rendered, **then** the text is escaped and no executable external content is introduced.
5. **Given** the final branch, **when** focused and full verification run, **then** they pass with no changes outside the declared scope.

## Risks and recovery

- **Risk**: Host support for MCP Apps varies. **Mitigation**: preserve a normal textual/structured tool result in addition to the UI resource.
- **Risk**: Runtime status may become stale between reads. **Mitigation**: build the HTML resource from a fresh snapshot on every resource read and timestamp it.
- **Risk**: A standalone app cannot safely call main-gateway mutation tools. **Mitigation**: this slice is intentionally read-only and labels operational actions as commands to invoke through the existing gateway.
- **Recovery**: Revert the feature commit. No data migration, persistent state mutation, dependency change, or Desktop Commander change is involved.

## Out of scope

- Mounting the app into `build_server()` while that file is owned by active change `035-llm-capability`.
- Restoring quarantine items, launching processes, running verification, or changing provider configuration from the UI.
- Customizing or forking Desktop Commander UI assets.
- Adding JavaScript frameworks, web build tooling, package dependencies, authentication, telemetry, or external content.
