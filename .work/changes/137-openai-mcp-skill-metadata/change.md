# Change: Openai Mcp Skill Metadata

- **Change ID**: `137-openai-mcp-skill-metadata`
- **Risk Profile**: lean

## Outcome

Register renamed OpenAI MCP skill identities and first-class metadata

## Scope and acceptance

- Development level: Small; one settings contract plus its pinned completeness test.
- Replace retired `build-mcp-*` metadata keys with the three renamed skill identities.
- Add first-class capability metadata for `mcp-development`.
- Keep every active MCP skill categorized with non-empty capabilities and activation terms.
- Reject regression to the three retired MCP skill IDs in the capability-settings test.

## Implementation and verification

- Implementation notes: updated `settings/capabilities.settings.json`; adjusted the exact metadata-count assertion and added renamed/retired-ID assertions.
- Focused checks: capability settings + dynamic Skills catalogue tests passed, 8/8; change governance `validate` and `check` passed.
- Review findings: focused NVIDIA nano code-quality review completed with zero findings.
- Residual risk: running `kis-op`/`kis-dev` processes retain their startup settings until refreshed/restarted; repository merge establishes the next-runtime authority.
- Closeout state: ready for commit, publication, exact-head CI, and merge.
