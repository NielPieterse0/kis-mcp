# Change: Agnix Mcp Schema Validation

- **Change ID**: `242-agnix-mcp-schema-validation`
- **Risk Profile**: lean

## Outcome

Make pinned strict agnix validation ignore only non-agent MCP schema artifacts while preserving real validation coverage.

## Scope and acceptance

- Add one repository-local agnix configuration that excludes only `contracts/tools/mcp-sdk-integrations/mcp-spec.schema.json` from agent-configuration linting.
- Keep AGENTS.md and genuine MCP configuration files in validation scope.
- Prove pinned agnix 0.45.0 strict validation no longer emits the known false `MCP-002` errors from that schema document.
- Prove an intentionally malformed MCP configuration remains detectable by strict validation.
- Add deterministic regression checks for the narrow exclusion and preserve the pinned agnix version/install contract.

## Implementation and verification

- Implementation notes: added `.agnix.toml` with one exact contract-schema exclusion and pinned `spec_revisions.mcp_protocol = "2026-07-28"`; no agnix runtime or install settings changed.
- Focused checks: agent-validation tests 9/9 pass; `git diff --check` passes; governance `check` passes. Live pinned agnix 0.45.0 strict validation reports 0 errors on this worktree, and an isolated malformed `.mcp.json` still reports `MCP-022` as an error.
- Review findings: code-quality and test-quality agent reviews completed with no actionable findings.
- Residual risk: agnix warnings on AGENTS.md remain visible and intentionally out of this false-positive slice; the exclusion is exact-path only.
- Closeout state: canonical repository verification passed; ready for publication and exact-head verification.
