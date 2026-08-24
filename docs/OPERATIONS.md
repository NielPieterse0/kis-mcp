# Operations

## Authority boundary

`docs/OPERATIONS.md` is the canonical operator entry point for installation, configuration, startup, commissioning, verification, troubleshooting, and recovery. Detailed procedures live in the linked `docs/operations/**` runbooks and are subordinate parts of this same operator-documentation domain.

Repository workflow and documentation routing belong to [`../AGENTS.md`](../AGENTS.md). Current architecture and implementation status belong to [`../SPEC.md`](../SPEC.md). Trust semantics belong to [`TRUST-MODEL.md`](TRUST-MODEL.md). Target architecture belongs to [`PLATFORM-CONCEPT.md`](PLATFORM-CONCEPT.md). Executable values remain authoritative in the applicable settings, contracts, source, scripts, and tests.

Load only the runbook needed for the operator task. Do not read every runbook by default.

## Operator task index

| Task | Runbook |
|---|---|
| Prerequisites, deployment model, state layout, dependency/bootstrap installation, Desktop Commander, AgentSys/agnix, Desktop Commander upgrades | [`operations/setup.md`](operations/setup.md) |
| Canonical JSON configuration and settings ownership | [`operations/configuration.md`](operations/configuration.md) |
| Local stdio startup, capability dispatch, Control Center, long-lived tool-binding diagnosis | [`operations/runtime.md`](operations/runtime.md) |
| Provider status, DBHub/Docker Hub activation and commissioning, GitHub OAuth, Supabase OAuth | [`operations/providers.md`](operations/providers.md) |
| NVIDIA/Codex advisory review-agent setup and use | [`operations/review-agent.md`](operations/review-agent.md) |
| Work Management and Discover operator workflows | [`operations/work-discover.md`](operations/work-discover.md) |
| Deterministic post-merge observer, exact landed-scope identity, bounded evidence failures, commissioning runner, durable live-verification evidence, recovery, and live release verification | [`operations/post-merge-commissioning.md`](operations/post-merge-commissioning.md) |
| Local ChatGPT HTTP smoke, tunnel profiles, `kis-op` / `kis-dev`, ChatGPT app commissioning | [`operations/chatgpt-remote.md`](operations/chatgpt-remote.md) |
| Governed parallel changes and repository verification | [`operations/verification-changes.md`](operations/verification-changes.md) |
| Quarantine, restore, and troubleshooting | [`operations/recovery-troubleshooting.md`](operations/recovery-troubleshooting.md) |

## Baseline prerequisites

- Windows with PowerShell.
- Python and `uv` versions accepted by the repository bootstrap/locked project metadata.
- Node.js and npm versions accepted by the Desktop Commander installer/package metadata.
- Direct operator supervision for bootstrap and upgrades.

For deployment/state details, use [`operations/setup.md`](operations/setup.md).

## Common fast paths

Run commands from `C:\Projects\kis-mcp` unless a runbook says otherwise. Bootstrap and upgrades that require external network access are explicit operator-supervised actions outside normal Work.

### Bootstrap and local startup

```powershell
pwsh -File .\scripts\bootstrap-python.ps1
pwsh -File .\scripts\prepare-desktop-commander-cache.ps1
pwsh -File .\scripts\install-desktop-commander.ps1
pwsh -File .\scripts\start.ps1
```

For exact installation, state, and configuration requirements, use [`operations/setup.md`](operations/setup.md) and [`operations/configuration.md`](operations/configuration.md). For local runtime/provider behavior, use [`operations/runtime.md`](operations/runtime.md) and [`operations/providers.md`](operations/providers.md).

### Verification

During development, run focused affected checks. The normal pull request to `main` owns the single canonical full repository verification pass on the exact GitHub head.

For an explicit local canonical run outside that PR path:

```powershell
pwsh -File .\scripts\verify.ps1
```

The detailed verification contract and change-worktree lifecycle are in [`operations/verification-changes.md`](operations/verification-changes.md).

### Governed change lifecycle

Create a governed change only when version-controlled repository content changes. From a clean primary `main` checkout, create the isolated change with the repository workflow:

```powershell
pwsh -File .\scripts\change-workflow.ps1 new example-change --allocate-next --outcome "Implement one bounded result" --complexity small --owned "src/example/**"
```

`--allocate-next` atomically assigns the numeric prefix and prints the resulting canonical change ID. Before publication, run `pwsh -File .\scripts\change-workflow.ps1 check` from that change worktree. After verified merge, run `pwsh -File .\scripts\change-workflow.ps1 cleanup <change-id>` from clean primary `main`.

Use [`../AGENTS.md`](../AGENTS.md) for governing semantics and [`operations/verification-changes.md`](operations/verification-changes.md) for the operator procedure.

### ChatGPT-facing instances

The configured instances are `kis-op` on `127.0.0.1:8010` and `kis-dev` on `127.0.0.1:8011`.

```powershell
pwsh -File .\scripts\start-chatgpt.ps1 kis-op
pwsh -File .\scripts\start-chatgpt.ps1 kis-dev
```

`kis-op` and `kis-dev` may run concurrently. Startup is instance-scoped: the peer instance is neither inspected for cleanup nor stopped. The launcher reclaims a selected-instance listener or orphan process tree only when it positively matches the selected KIS runtime identity; otherwise it fails with `KIS_MCP_PORT_OWNED_BY_OTHER_PROCESS`. Each selected instance records generated lifecycle/ownership evidence in its own `current.json`; that record does not override current process/listener evidence, canonical settings, or repository authority.

Tunnel configuration, startup ownership, local smoke checks, and ChatGPT app commissioning are in [`operations/chatgpt-remote.md`](operations/chatgpt-remote.md).

### Provider and workflow operations

- Provider readiness/authentication/commissioning: [`operations/providers.md`](operations/providers.md).
- Advisory code-review agent: [`operations/review-agent.md`](operations/review-agent.md).
- Work Management and Discover: [`operations/work-discover.md`](operations/work-discover.md).
- Capability discovery and local runtime: [`operations/runtime.md`](operations/runtime.md).

### Recovery

Delete-like Work intent must remain recoverable under HR-003. Use the quarantine and restore procedures in [`operations/recovery-troubleshooting.md`](operations/recovery-troubleshooting.md); permanent disposal is not a normal Work operation.

When diagnosing an operational failure, start with the relevant scoped runbook instead of searching this index for implementation details.
