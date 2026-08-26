# Change Specification: FastMCP 4 Proxy Loop Startup

- **Change ID**: `240-fastmcp4-proxy-loop-startup`
- **Status**: Approved by direct operator instruction to fix `kis-dev`
- **Risk Profile**: rigorous
- **Development level**: Complex — provider/runtime architecture boundary and live operational recovery

## Outcome

Restore `kis-dev` startup on FastMCP 4 without stopping, restarting, reconfiguring, or otherwise modifying `kis-op`.

## Authority and scope

- Authoritative sources: `AGENTS.md`, existing Work #475 / Change 239 outcome, current FastMCP 4 runtime behavior, and the live failure evidence from `kis-dev`.
- Owned paths: `src/kis_mcp/gateway/composition.py`, `tests/**`, and this change record.
- Excluded: `kis-op` lifecycle/state, provider activation changes, unrelated MCP 2026 behavior, dependency/version changes.
- Work binding: `WORK-475`, source issue `NielPieterse0/kis-mcp#475`.

## Requirements

- **REQ-001**: Gateway construction MUST NOT connect the actual runtime proxy/provider graph on a disposable `asyncio.run()` event loop.
- **REQ-002**: The capability catalogue MUST retain local KIS tools, approved Desktop Commander tools, and declared mounted-provider operations without requiring the actual mounted proxies to connect during construction.
- **REQ-003**: Any Desktop Commander discovery needed before runtime MUST use an isolated disposable proxy whose stdio session is fully closed before its event loop closes.
- **REQ-004**: `kis-dev` MUST initialize and become ready under the locked FastMCP 4 environment without `Event loop is closed` failures.
- **REQ-005**: `kis-op` MUST remain on the same running server instance throughout repair and commissioning.
## Acceptance

1. A regression test proves composition does not call `list_tools()` across the actual aggregate runtime proxy graph.
2. Capability tests prove declared mounted-provider operations remain represented and eligible/readiness-gated as before.
3. Focused gateway/provider tests pass on the exact working tree.
4. A live `kis-dev` startup reaches readiness on port 8011 with no closed-event-loop traceback.
5. `kis-op` PID/server instance evidence is unchanged before and after live commissioning.

## Risks and recovery

- Risk: reducing aggregate pre-runtime discovery could accidentally hide approved runtime operations.
- Mitigation: retain local tool schemas, use isolated Desktop Commander discovery, and project declared mounted-provider operations without connecting their live proxies.
- Recovery: revert Change 240; no persistent data or schema migration is introduced.

## Out of scope

- Changing FastMCP/MCP package versions.
- Restarting or upgrading the running `kis-op` process.
- Redesigning provider authentication, Work Management, or MCP 2026 Tasks semantics.
