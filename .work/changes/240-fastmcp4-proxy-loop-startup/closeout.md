# Closeout: FastMCP 4 Proxy Loop Startup

## Implemented scope

- Replaced construction-time aggregate `server.list_tools()` enumeration with non-proxy provider discovery.
- Added isolated Desktop Commander discovery through `StdioTransport(..., keep_alive=False)`.
- Preserved mounted-provider capability metadata through declared provider operations and existing runtime refresh.
- Updated the commissioning-order regression for the new snapshot construction.

## Validation evidence

- TDD regression failed on the pre-fix aggregate enumeration path, then passed after implementation.
- Focused current-state suite: 10/10 passed (`tests/gateway/test_composition.py`, isolated discover registration test, and `tests/capabilities/test_gateway_composition.py`).
- Production composition smoke: `build_server()` completed as `FastMCPProxy('kis-mcp')` without `Event loop is closed`.
- Bounded worktree `kis-dev` probe reached `health=ready` on `http://127.0.0.1:8011/mcp`; the observation probe then stopped itself normally. `kis-op` remained the same server instance (`578b8b4d9ba5408f833129f9134a556b`) and the same operation process lineage (`27708` / child `17848`).
- Serena logged validation warnings for the MCP 2026 `server/discover` extension during provider discovery, but the provider continued to list tools and `kis-dev` reached ready; this is non-blocking for the startup defect fixed here.
- Governed `change-workflow.ps1 check`: passed.
- Local full verification reached two failures: one stale composition-string assertion fixed in this change; one shared evidence-generation conflict passed immediately in isolation. Per `AGENTS.md`, canonical full verification is PR-owned on the exact GitHub head.
- Ruff is not configured in the repository development dependency group; repository verification supplies Python syntax coverage.

## Review

- Architecture review: clean, no blocking findings.
- Code-quality review findings were dispositioned: graph traversal's shared visited set is valid cycle handling; enumeration remains intentionally fail-fast; `keep_alive=False` is required by the defect boundary; provider operations have a typed `enabled` contract; existing curated-surface tests already prove retained safe/local tools.
- Test-quality warnings were dispositioned: live startup is an operational acceptance gate rather than a unit composition gate, and the regular `FastMCP` curated-surface test already exercises retained non-proxy tools.

## Git and merge

- Branch: `change/240-fastmcp4-proxy-loop-startup`
- Worktree: `.work/worktrees/240-fastmcp4-proxy-loop-startup`
- Commit:
- Pull request or merge:
- Cleanup:

## Residual items

- Publish exact commit, obtain exact-head GitHub Actions/Work readiness, merge through KIS, re-commission merged `main`, complete Work #475, and clean Change 240.