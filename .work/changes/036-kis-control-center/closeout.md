# KIS Control Center Closeout

- **Status**: Implementation complete; ready for integration
- **Change ID**: `036-kis-control-center`
- **Development level**: Medium
- **Review**: No Critical or Important findings remain

## Implemented scope

- Added a focused `kis_mcp.control_center` package with immutable contracts, strict JSON settings, bounded local snapshot collection, a self-contained HTML renderer, and a standalone FastMCP server.
- Exposed one model-visible `open_kis_control_center` tool linked to `ui://kis-mcp/control-center.html` with MIME type `text/html;profile=mcp-app`.
- Added structured fallback content for hosts that do not render MCP Apps.
- Reports runtime identity, Desktop Commander installation evidence, exact three-rule policy status, local project/Git state, provider configuration with explicit runtime-check requirements, quarantine counts, verification guidance, and diagnostics.
- Added `settings/control-center.settings.json` and a strict JSON Schema.
- Added operator documentation and 13 focused tests.
- Did not modify, vendor, wrap, or fork Desktop Commander and did not modify the primary gateway integration files owned by another active change.

## Safety and truthfulness

- The app exposes no mutation tools and performs no network access.
- HTML contains no external scripts, styles, images, fonts, frames, or requests.
- Runtime-derived text is HTML-escaped.
- JSON inputs and quarantine metadata are byte-bounded.
- Git inspection uses a fixed local command, a timeout, a project ceiling, and removes inherited repository override variables.
- Provider configuration is labelled `runtime_check_required`; it is not presented as authentication, commissioning, connectivity, or readiness evidence.
- Verification remains `not_recorded` until the configured command is run through the supervised Work surface.

## Review findings resolved

- Renamed Control Center test modules to globally unique basenames after repository-wide pytest exposed an import-name collision.
- Added explicit JSON byte limits after review identified an unbounded local-read path.
- Added regression coverage and sanitization for inherited `GIT_DIR`, `GIT_WORK_TREE`, and related variables.
- Applied the same input bound to quarantine metadata.

## Verification evidence

- Focused Control Center tests: **13 passed**.
- `pwsh -NoProfile -File scripts/change-workflow.ps1 check`: passed and reported only declared paths.
- `git diff --check`: passed.
- JSON validation: both Control Center settings and schema passed.
- `pwsh -NoProfile -File scripts/verify.ps1`: passed; repository test suite completed with the existing two skips, and configuration, interpreter, dependency, syntax, line-ending, and change-governance checks were green.

## Recovery

Revert the feature commit. The slice creates only read-only source, tests, JSON settings/schema, and documentation; it performs no migration, dependency change, provider-state mutation, or Desktop Commander change.

## Residual boundary

- The Control Center is a standalone MCP App server invoked with `python -m kis_mcp.control_center`.
- Mounting it into the primary `build_server()` surface is intentionally deferred because `src/kis_mcp/server.py` was exclusively owned by active change `035-llm-capability` during this slice. The standalone app remains complete and independently deployable.
- Host support for MCP App rendering varies; structured fallback content remains available.

## Governance disposition

The scope is closed, ownership is disjoint, change-workflow checks pass, full verification is green, and no merge blocker remains.
