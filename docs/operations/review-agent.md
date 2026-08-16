# Code Review Agent

> Operator runbook subordinate to [Operations](../OPERATIONS.md). The current review-agent interface, selectors, result/error schemas, safety guarantees, backend state machine, and model/profile values belong to [SPEC.md](../../SPEC.md), agent settings/schema, source, and tests.

## Configure and use the code-review agent

Use [`../../settings/agents/code-review-agent.settings.json`](../../settings/agents/code-review-agent.settings.json) to inspect the currently configured backends, preferred/fallback order, models/profiles, budgets, and non-secret credential references. Do not duplicate those values here.

### Configure NVIDIA credentials

Resolve the configured NVIDIA secret reference from agent settings, then store/replace that credential through the supervised secret path:

```powershell
$AgentSettings = Get-Content .\settings\agents\code-review-agent.settings.json -Raw | ConvertFrom-Json
pwsh -NoProfile -File .\scripts\set-secret.ps1 -Reference $AgentSettings.nvidia.secret_ref
```

For an existing vault, configure the non-interactive runtime unlock once from a supervised local terminal:

```powershell
pwsh -NoProfile -File .\scripts\configure-secret-runtime-unlock.ps1
```

Never persist the API key or vault unlock in repository JSON, `.env`, command arguments, retained logs, or MCP requests.

### Configure Codex CLI review

Install the exact repository-configured Codex package through the supervised installer, then authenticate its managed profile with the intended ChatGPT account:

```powershell
pwsh -NoProfile -File .\scripts\install-codex.ps1
pwsh -NoProfile -File .\scripts\auth-codex.ps1
```

Use agent settings/source/readiness to determine the current managed paths, expected version, and authentication requirements.

### Run a review

Invoke `review_change_with_agent` against the intended project/change source. A minimal working-tree request is:

```json
{
  "path": "C:\\Projects\\example",
  "source": "working_tree"
}
```

Add a configured backend/model or specialist review type only when needed, using the operation schema and current agent settings as the accepted-value authority. Explicit backend selection is useful when verifying one reviewer independently.

Treat review provenance as part of the evidence:

- the review must cover the intended source/fingerprint;
- incomplete/omitted evidence is not a pass;
- timeout or invalid backend output is not a pass;
- findings must be resolved or explicitly dispositioned before closeout;
- any source edit invalidates the affected review and requires re-review.

The review operation is advisory. Do not use its result to authorize writes, bypass repository governance, or replace deterministic verification.

### Troubleshooting

If a backend is unavailable, inspect current agent/provider readiness and the configured credential/version prerequisites. If the combined review package exceeds the evidence budget, review bounded exact-source subsets and pair them with deterministic whole-change audits rather than claiming an incomplete aggregate review succeeded.

Use source/tests for current fallback, deadline, mutation-detection, response-schema, and error semantics; this runbook intentionally does not restate those contracts.