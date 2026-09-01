# Independent Recovery Read Implementation Plan

> **For agentic workers:** Execute this plan task-by-task and keep the declared scope current.

**Goal:** Make repository diagnostics available through the existing local-shell recovery surface when MCP/tunnel transport is unavailable.

**Architecture:** Add one bounded `-ReadPath` mode before launcher resolution in `recover-kis-dev.ps1`; keep launch semantics unchanged; document the transport-error distinction.

**Tech Stack:** PowerShell 7, Python/pytest, governed change workflow.

## Constraints

- Stay inside `scope.json`; do not mutate the sibling `mcp-tool` checkout/runtime.
- Never touch `kis-op` runtime availability.
- Preserve failed MCP operations as errors; do not reinterpret 404/429/5xx as successful reads.

## Tasks

1. Reproduce the legacy independent connector failure and localize its boundary.
2. Add failing tests for local-shell read success and unsafe-path rejection.
3. Implement bounded UTF-8 repository reads with traversal/reparse/size guards.
4. Document the distinction between tolerated OAuth discovery 404 and failed MCP operations.
5. Run focused verification and live local-shell read evidence.
6. Run governed check, specialist review, exact-head CI, merge, documentation reconciliation, Work completion, and cleanup.