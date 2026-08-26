# Runtime

> Operator runbook subordinate to [Operations](../OPERATIONS.md). Current runtime architecture/provider composition belongs to [SPEC.md](../../SPEC.md); executable composition and surface truth belongs to settings/contracts/source/tests and current runtime status.

## Start local stdio

Run from the source checkout:

```powershell
pwsh -File .\scripts\start.ps1
```

Startup requires the repository's locked external Python environment and configured local provider prerequisites. If startup reports a provider/configuration/readiness error, inspect the named settings and [`providers.md`](providers.md) rather than changing policy or copying runtime composition into this document.

### Skill usage telemetry

Use the Skills operations when you need operational telemetry for an actual skill activation:

1. Load the skill with a stable activation/project identity when available.
2. After actual application/completion/failure, record the outcome against the observed load identity.
3. Query the telemetry report with the relevant skill/project/version filters.

A load is not evidence that a skill was applied. Telemetry is operational evidence, not authorization or product-quality authority. Use the Skills operation schemas/source for current identifiers, bounds, fields, and storage behavior.

## Use capability discovery and long-tail execution

Use capability discovery when an operation is not already a direct tool:

- `search_capabilities` to locate eligible operations;
- `describe_capability` to inspect one operation;
- `recommend_workflow` for task-level routing;
- `execute_read_action`, `execute_change_action`, or `execute_external_action` according to the operation's declared effect.

The operation's original schema, current readiness, provider authentication, and normal middleware remain authoritative. Do not infer eligibility or approval from a recommendation score or this runbook.

## Run the KIS Control Center

Use the mounted read-only Control Center operation when available. To run the standalone app from the source checkout:

```powershell
C:\Projects\.kis-mcp\python-env\Scripts\python.exe -m kis_mcp.control_center
```

Treat its snapshot as current operational evidence only. Provider configuration does not prove authentication/commissioning, and runtime status does not supersede repository settings, Git, contracts, or product authority.

## Long-running MCP Tasks

FastMCP 4 exposes selected long operations as optional MCP Tasks: `run_verification`, `review_change_with_agent`, `kis_post_merge_commissioning_run`, and `prepare_reviewable_pull_request`. Clients that advertise `io.modelcontextprotocol/tasks` may receive a task ID and poll `tasks/get`; clients without Tasks support receive the compatible synchronous result path.

Treat the MCP task ID as a transport handle, not KIS authority. Work records, execution IDs, receipts, revisions, and coordinator fences remain authoritative. A client may disconnect and reconnect to the same running KIS service and continue task retrieval by task ID. Current MCP task storage is process-local, so do not claim that the same task ID survives a KIS server-process restart; follow-up Work #498 owns that future trigger.

For verification, distinguish the caller/request budget from the verification execution deadline, stall timeout, and MCP task TTL. Progress is bounded activity evidence. Cancellation is cooperative; when KIS owns the verification child PID it attempts process termination, but a cancellation request alone is not proof of a durable cancelled Work state.

## Diagnose long-lived ChatGPT tool binding

When an older chat appears unable to use `kis-op` or `kis-dev`:

1. Do not restart KIS first.
2. Call `kis_health` from the affected chat if possible and record the returned runtime/contract identity fields.
3. Open a new chat against the same app/runtime and call the same `kis_health`.
4. Open Control Center and compare recent boundary request records/timestamps for the attempts.
5. If the old attempt produced no inbound record while the new attempt did, investigate ChatGPT/app binding outside KIS. If both reached KIS, diagnose the recorded KIS outcome before restarting anything.

Use current `kis_health`/Control Center schemas for exact diagnostic fields. Do not enable prompt/body logging to diagnose this class of issue.