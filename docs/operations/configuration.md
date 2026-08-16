# Configuration

> Operator runbook subordinate to [Operations](../OPERATIONS.md). Current architecture belongs to [SPEC.md](../../SPEC.md); JSON, schemas, source, and tests own executable values and field contracts.

## Configure

Edit the smallest applicable canonical JSON owner. Do not copy current values into this runbook.

| Operator concern | Canonical configuration |
|---|---|
| Core identity, paths, Desktop Commander, Discover retrieval, local/remote runtime | [`../../settings/kis-mcp.settings.json`](../../settings/kis-mcp.settings.json) |
| Mounted provider selection | [`../../settings/providers/platform-runtime.provider.json`](../../settings/providers/platform-runtime.provider.json) |
| Individual provider installation/runtime metadata | applicable `settings/providers/*.provider.json` |
| Registered project identities and provider bindings | [`../../settings/projects.settings.json`](../../settings/projects.settings.json) |
| Work Management modes/bindings | [`../../settings/work-management/github-projects.settings.json`](../../settings/work-management/github-projects.settings.json) |
| GitHub Project desired schema/view manifest | [`../../settings/work-management/github-project-schema.json`](../../settings/work-management/github-project-schema.json) |
| Review-agent backends/budgets | [`../../settings/agents/code-review-agent.settings.json`](../../settings/agents/code-review-agent.settings.json) |
| Capability exposure/ranking metadata | [`../../settings/capabilities.settings.json`](../../settings/capabilities.settings.json) |
| Work hard-rule declaration | [`../../policy/kis-mcp.policy.json`](../../policy/kis-mcp.policy.json) |

Use the adjacent schemas/contracts/tests to determine allowed fields, values, and invariants. Never infer a current port, revision, provider list, field count, project membership, or readiness state from prose.

Credentials and secret values must not be stored in repository JSON. Store only the repository-approved non-secret references/metadata and use the supervised credential/vault procedures referenced by the relevant provider/runtime runbook.