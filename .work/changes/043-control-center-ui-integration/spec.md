# Change Specification: Control Center UI Integration

- **Change ID**: `043-control-center-ui-integration`
- **Status**: Approved
- **Development level**: Complex
- **Risk Profile**: rigorous

## Outcome

Integrate the existing KIS Control Center MCP App into the primary provider runtime and expand it into a truthful, read-only operational dashboard without modifying, wrapping, vendoring, or forking Desktop Commander.

## Authority and scope

- Authoritative sources: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, `policy/kis-mcp.policy.json`, and the operator-approved UI direction supplied for this slice.
- Integration seam: register `control-center` as a local read-only provider and enable it through `settings/providers/platform-runtime.provider.json`; do not modify `src/kis_mcp/server.py` while change `040-context7-serena-adapters` owns that file.
- Desktop Commander remains authoritative for its file preview, editor, directory browser, document rendering, and settings widgets.
- The Control Center remains a separate KIS-owned module and must not create a second Work policy boundary.
- All settings remain JSON and all runtime evidence is bounded.

## Requirements

- **REQ-001 — Primary gateway integration**: The platform provider registry SHALL register a `control-center` provider with `ProviderBoundary.LOCAL_READ_ONLY`; provider runtime settings SHALL enable it under namespace `control_center` so the normal kis-mcp connector exposes its tool and MCP App resource.
- **REQ-002 — Separation**: The implementation SHALL NOT modify Desktop Commander installation content or duplicate its file, editor, directory, preview, or configuration widgets.
- **REQ-003 — Runtime health and project**: The dashboard SHALL display current runtime identity, Desktop Commander installation evidence, configured project path, bounded local Git state, and exact snapshot time.
- **REQ-004 — Policy and approvals**: The dashboard SHALL display the exact HR-001, HR-002, and HR-003 declarations, bounded recent policy decisions, and bounded pending operator decisions parsed from the existing hard-block approval register without modifying that register.
- **REQ-005 — Discover summary**: The dashboard SHALL run bounded local `inspect_project` logic through the existing Discover service and display project identity, language/framework/module counts, findings, confidence, truncation, and diagnostics. Discover failure SHALL degrade only that section.
- **REQ-006 — Provider readiness**: The dashboard SHALL display provider registration, enablement, readiness, build/mount state, actionable status, and commissioning evidence where available. Configuration alone SHALL never be represented as authentication, connectivity, or live verification.
- **REQ-007 — Runtime observability**: The gateway SHALL keep bounded in-memory records for recent tool calls, policy decisions, active managed processes, and active searches. Records SHALL exclude raw argument values and result bodies.
- **REQ-008 — Quarantine and verification**: The dashboard SHALL show bounded quarantine records, available quarantine/restore tool names, and current verification evidence state. The UI SHALL not directly mutate files, restore records, or execute verification.
- **REQ-009 — UI behavior**: The MCP App SHALL be self-contained, responsive, host-theme aware, accessible, deterministic, and free of external scripts, styles, fonts, frames, images, or requests. Runtime-derived text SHALL be escaped.
- **REQ-010 — Compatibility**: The standalone `python -m kis_mcp.control_center` entry point SHALL continue to work, while the primary gateway integration SHALL require no second manually started server.
- **REQ-011 — Verification**: Tests SHALL prove provider registration and namespaced mounting, MCP App metadata/resource visibility, bounded observability, secret-safe records, approval parsing, Discover degradation, provider-state truthfulness, rendering safety, and full repository compatibility.

## Acceptance

1. **Given** the normal `build_server()` provider composition, **when** tools and resources are listed, **then** the Control Center entry tool and `ui://kis-mcp/control-center.html` resource are available without starting a second process.
2. **Given** recent allowed, blocked, process, and search calls, **when** the dashboard snapshot is collected, **then** bounded redacted runtime records appear and no raw argument value or result body is retained.
3. **Given** the approval register contains unchecked operator decisions, **when** the snapshot is collected, **then** those entries appear as pending approvals without modifying the document.
4. **Given** Discover or provider evidence is unavailable, **when** the dashboard opens, **then** the affected section reports an explicit degraded or unknown state while the rest remains usable.
5. **Given** hostile local text, **when** the UI is rendered, **then** it is escaped and no external executable content is introduced.
6. **Given** the final branch, **when** focused tests, scope checks, whitespace checks, and `scripts/verify.ps1` run, **then** they pass on the exact reviewed head.

## Risks and recovery

- **Risk — provider namespace behavior**: mounting may rename tools or affect resource discovery. Mitigation: FastMCP client integration tests against the composed provider runtime.
- **Risk — observability leakage**: tool arguments may contain secrets or sensitive text. Mitigation: retain only tool name, argument key names, decision/status, timestamp, and bounded identifiers explicitly extracted for process/search lifecycle.
- **Risk — expensive Discover refresh**: repository inspection may be slow. Mitigation: use configured Discover budgets, catch failure per section, and avoid repository-code execution or network access.
- **Risk — stale in-memory state**: observability covers only the current gateway process. Mitigation: label scope and timestamp explicitly; do not claim persisted history.
- **Recovery**: revert the feature commits and remove the `control-center` runtime provider entry. No migration, provider credential change, Desktop Commander change, or persistent state conversion is introduced.

## Out of scope

- Redesigning ChatGPT, Claude, or Desktop Commander host chrome.
- Forking or modifying Desktop Commander MCP App resources.
- Direct UI-triggered mutation, restore, process termination, verification execution, provider authentication, or settings changes.
- Persistent telemetry, external analytics, remote storage, browser hosting, or new package dependencies.
- Changes to `server.py`, startup scripts, `settings/kis-mcp.settings.json`, `SPEC.md`, `docs/OPERATIONS.md`, policy files, or the approval register.
