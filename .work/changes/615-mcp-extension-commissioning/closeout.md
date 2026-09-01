# Closeout: Mcp Extension Commissioning

## Implemented scope

- Added reusable in-process MCP-extension commissioning with typed PASS/FAIL receipts bound to process, unique server instance, source revision, protocol version, extension identity/settings, and profile evidence.
- Added SEP-2640 Skills commissioning across discovery, list/get, entrypoint integrity, directory read, and unnegotiated METHOD_NOT_FOUND controls for every negotiation-gated method.
- Extended Skills telemetry additively with negotiated extension, commissioning receipt, server/runtime identity, canonical URI, resource-set integrity, and commissioned-vs-uncommissioned reporting without payload retention.

## Validation evidence

- Focused checks: 40 targeted architecture/commissioning/telemetry/tool-registration tests passed after final review fixes.
- Repository verification: `scripts/verify.ps1` passed on the final working tree; full pytest reached 100% with only pre-existing FastMCP deprecation warnings.
- Diff scope check: `scripts/change-workflow.ps1 check` passed with only declared #621 paths and no #620 commissioning observer paths.

## Review

- Findings: initial independent architecture review found three blockers; API-contract review found two blockers.
- Resolutions: added unique per-server identity, per-request negotiated attribution, exact receipt/runtime correlation, stable typed failure codes, and negative-negotiation evidence for list/get/directory-read. Architecture re-review passed before the final dependency-direction refinement; the final refinement is covered by the architecture guard and full repository verification. Large combined review projections may require exact-diff/manual fallback because reviewer evidence truncates at its bounded evidence limit.

## Git and merge

- Branch: `change/615-mcp-extension-commissioning`
- Worktree: `.work/worktrees/615-mcp-extension-commissioning`
- Commit:
- Pull request or merge:
- Cleanup:

## Residual items

-
