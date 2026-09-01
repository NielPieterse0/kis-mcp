# Change Specification: Independent Recovery Read

- **Change ID**: `620-independent-recovery-read`
- **Status**: Active
- **Complexity**: medium

## Outcome

Provide a KIS-owned bounded repository read on the existing local-shell `kis-dev` recovery surface so diagnostics do not depend on a selected MCP runtime or tunnel.

## Authority and scope

- Authority: `AGENTS.md`, issue #626, and `docs/operations/recovery-troubleshooting.md`.
- Owned: `scripts/recover-kis-dev.ps1`, `tests/test_startup_scripts.py`, recovery runbook, and this change record.
- Dependencies: none; #609 is evidence for tolerated no-auth OAuth discovery only.
- The sibling `mcp-tool` checkout/runtime is evidence only and is not mutated.

## Requirements

- **REQ-001**: `-ReadPath` reads only repository-relative UTF-8 files without starting or contacting KIS runtimes/tunnels.
- **REQ-002**: traversal, reparse points, missing files, binary content, and reads above 1 MiB fail deterministically.
- **REQ-003**: existing foreground/detached `kis-dev` recovery behavior remains unchanged.
- **REQ-004**: documentation distinguishes tolerated OAuth discovery 404 from failed MCP operations such as `invalid_mcp_response` on 404, 429, or 5xx.
- **REQ-005**: focused tests, governed check, review, and live local-shell read evidence pass before promotion.

## Acceptance

1. Given the MCP/tunnel path is unusable, when `recover-kis-dev.ps1 -ReadPath AGENTS.md` runs, then it returns the file through a structured local-shell result without touching `kis-op`.
2. Given an invalid or escaping read path, when recovery read runs, then it fails with a bounded `KIS_DEV_RECOVERY_READ_*` error.
3. Given an MCP operation probe failure, then it remains an error and is never reclassified as the optional OAuth-discovery 404 case.

## Out of scope

- Repairing or mutating the separate `mcp-tool` repository/runtime or its platform-managed tunnel.