# Change Specification: Skills MCP Resources

- **Change ID**: `192-skills-mcp-resources`
- **Parent**: Change 186 / issue #356
- **Work item**: issue #362
- **Historical source**: Change 174 branch through `5cf2406`
- **Protocol authority**: FastMCP `3.4.4` + normative MCP `2025-11-25` only

## Outcome

Restore canonical Skills as read-only MCP Resources plus delivery attribution telemetry without introducing a custom transport contract or adopting FastMCP 4.x/MCP 2026 assumptions.

## Requirements

- Expose the canonical Skills catalogue index as a deterministic MCP resource.
- Expose bounded catalogue continuation and skill entrypoint/supporting-file resource templates.
- Preserve exact validated snapshot bytes, path/link safety, stale-snapshot rejection, and data-only treatment for scripts/assets.
- Preserve explicit canonical entrypoint URI semantics so supporting-resource templates cannot alias `SKILL.md`.
- Record delivery attribution/telemetry without turning resource reads into proof that a Skill was applied or completed.
- Preserve identity-complete comparison semantics for delivery telemetry.
- Use FastMCP 3.4.4 resource registration and protocol serialization; do not implement custom `resources/*` transport handlers.

## Acceptance

Relevant Skills tests and Ruff pass; scope check passes; MCP/API-contract, architecture, and code-quality reviews are clean; GitHub Actions passes on the exact frozen head.