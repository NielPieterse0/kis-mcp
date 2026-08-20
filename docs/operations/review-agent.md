# Code Review Agent

> Operator runbook subordinate to [Operations](../OPERATIONS.md). The current review-agent interface, selectors, result/error schemas, safety guarantees, backend state machine, and model/profile values belong to [SPEC.md](../../SPEC.md), agent settings/schema, source, and tests.

## Configure and use the code-review agent

Use [`../../settings/agents/code-review-agent.settings.json`](../../settings/agents/code-review-agent.settings.json) to inspect reviewer budgets, liveness thresholds, backend readiness, and non-secret credential references. Automatic production review routing is purpose-specific and code-owned; it does not use the legacy preferred/fallback backend order as a universal reviewer policy.

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

Normally set only `review_type`; KIS then uses the qualified purpose-specific NVIDIA primary/backup route and SSE liveness handling for that lane. Explicit `backend` or legacy `model` selection is a compatibility/diagnostic override and disables automatic purpose-route fallback. Explicit `backend="codex-cli"` is direct only.

Treat review provenance as part of the evidence:

- the review must cover the intended source/fingerprint;
- incomplete/omitted evidence is not a pass;
- timeout, hard stall, truncation, unexpected tool calls, or invalid backend output are not a pass;
- automatic results include bounded SSE liveness telemetry; provider deltas are the heartbeat source;
- safety/security findings must survive deterministic corroboration and complete Super/Ultra adjudication cardinality;
- findings must be resolved or explicitly dispositioned before closeout;
- any source edit invalidates the affected review and requires re-review.

The review operation is advisory. Do not use its result to authorize writes, bypass repository governance, or replace deterministic verification.

### Troubleshooting

If a backend is unavailable, inspect current agent/provider readiness and the configured credential/version prerequisites. If the combined review package exceeds the evidence budget, review bounded exact-source subsets and pair them with deterministic whole-change audits rather than claiming an incomplete aggregate review succeeded.

Use source/tests for current fallback, deadline, mutation-detection, response-schema, and error semantics; this runbook intentionally does not restate those contracts.