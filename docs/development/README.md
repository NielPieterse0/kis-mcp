# Development History

`docs/development/**` is retained historical engineering evidence. It is **not normal implementation context** and does not define current product behavior, operator procedure, policy, configuration, or repository workflow.

For current work, start from the canonical owners routed by [`AGENTS.md`](../../AGENTS.md): current product truth in [`SPEC.md`](../../SPEC.md), operator procedure in [`OPERATIONS.md`](../OPERATIONS.md), trust semantics in [`TRUST-MODEL.md`](../TRUST-MODEL.md), and executable values in settings/contracts/source/tests.

## When to search this archive

Search here only when the task needs historical evidence, such as:

- tracing provenance or a prior architectural decision;
- investigating a regression or previously rejected approach;
- locating dated commissioning, verification, or migration evidence;
- understanding why a current invariant or compatibility boundary exists.

Do not load this subtree merely because a historical file mentions the component being changed. Do not copy historical status or values forward as current truth without re-verifying them against the current canonical owner.

## Evidence handling

- Treat records as evidence of their original point in time.
- Do not rewrite old evidence just to match the current implementation.
- If a historical finding remains durably relevant, promote the durable conclusion into its current canonical owner through a governed change.
- Prefer targeted search for the needed topic over broad traversal of the archive.

## Archive map

Use these categories to narrow a historical search:

| Topic | Historical areas |
|---|---|
| Bootstrap, startup, remote runtime | [`bootstrap/`](bootstrap/), [`startup-hardening/`](startup-hardening/), [`live-proxy-commissioning/`](live-proxy-commissioning/), [`chatgpt-remote-commissioning/`](chatgpt-remote-commissioning/) |
| Discover and modularity work | [`discover-foundation/`](discover-foundation/), [`discover-project-catalog/`](discover-project-catalog/), [`discover-provider-admission/`](discover-provider-admission/), [`discover-final-integration/`](discover-final-integration/), [`modularity-contracts/`](modularity-contracts/) |
| Provider and integration work | [`provider-module/`](provider-module/), [`provider-composition/`](provider-composition/), [`provider-runtime-composition/`](provider-runtime-composition/), [`provider-state-atomicity/`](provider-state-atomicity/), [`github-mcp-provider/`](github-mcp-provider/), [`supabase-mcp-provider/`](supabase-mcp-provider/) |
| Skills, SDK, and operator tooling | [`skills-module/`](skills-module/), [`mcp-sdk-integrations/`](mcp-sdk-integrations/), [`control-center/`](control-center/), [`tools/`](tools/) |
| GitHub/work-management history | [`git-workflow-tooling/`](git-workflow-tooling/), [`github-project-onboarding/`](github-project-onboarding/), [`github-default-branch-refresh.md`](github-default-branch-refresh.md), [`workflow-discovery-bridge.md`](workflow-discovery-bridge.md) |
| Safety and credential history | [`quarantine-integrity/`](quarantine-integrity/), [`secrets/`](secrets/) |

This map is navigational only. The archive can grow without requiring this index to enumerate every historical record.
