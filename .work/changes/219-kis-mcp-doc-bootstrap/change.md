# Change: KIS MCP Tool-User Bootstrap

- **Change ID**: `219-kis-mcp-doc-bootstrap`
- **Risk Profile**: lean

## Outcome

Register `kis-mcp-doc` and `kis-mcp-gov` as independently routable KIS tool-user projects, and register `kis-mcp-doc` in Work Management so its completed child implementation can continue through normal KIS publication and closeout.

## Scope and acceptance

- Register `kis-mcp-doc` at `C:\Projects\kis-mcp-doc` with GitHub repository `NielPieterse0/kis-mcp-doc`.
- Register `kis-mcp-gov` at `C:\Projects\kis-mcp-gov`.
- Preserve the Doc GitHub binding already prepared by this change.
- Keep Gov GitHub binding unset until independent Gov Git/GitHub identity is actually established.
- Both project IDs must load through the central `ProjectRegistry`, and repository catalogue tests must include the Doc GitHub binding.
- Register `kis-mcp-doc` in Work Management against `NielPieterse0/kis-mcp-doc` using the existing `github-default` Project binding.
- Work Management loading must resolve the child repository without `GITHUB_REPOSITORY_SCOPE_VIOLATION`.

## Implementation and verification

- Implementation notes: central registry plus Work Management managed-project registration; no child repository mutation from this parent change.
- Focused checks: project-registry, repository-registry, and GitHub Project commissioning tests passed 11/11; `scripts/change-workflow.ps1 check` and `git diff --check` passed.
- Review findings: code-quality clean; API-contract re-review clean after making the shared Work Management binding contract explicit in tests.
- Residual risk: live `kis-op` must be refreshed after merge before the child repository is published.
- Closeout state: implementation and local review/verification complete; publication/merge pending.
