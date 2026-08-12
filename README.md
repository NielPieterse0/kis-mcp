# kis-mcp

`kis-mcp` is a private, operator-supervised repository platform built on FastMCP and the authoritative Desktop Commander distribution.

It provides ordinary local development operations, bounded repository discovery, reusable Skills, explicit Provider and Tool composition, capability discovery and progressive exposure, advisory change review, provider-neutral work management, and a read-only Control Center. Current implementation truth belongs to [`SPEC.md`](SPEC.md); the approved target architecture belongs to [`docs/PLATFORM-CONCEPT.md`](docs/PLATFORM-CONCEPT.md).

The Work path enforces exactly three prohibited outcomes, whose semantics are owned by [`docs/TRUST-MODEL.md`](docs/TRUST-MODEL.md): writing outside `C:\Projects`, external network operations through local Work, and permanent deletion instead of recoverable quarantine.

## Documentation and authority

This README is the human landing page and navigation index. It does not independently define product behavior, policy doctrine, configuration values, or operator procedure.

Repository-wide documentation ownership and conflict routing are defined in [`AGENTS.md`](AGENTS.md). Use the canonical owner for detail:

| Need | Go to |
|---|---|
| Agent/repository workflow and documentation ownership | [`AGENTS.md`](AGENTS.md) |
| Current architecture, interfaces, and implementation state | [`SPEC.md`](SPEC.md) |
| Trust model and HR-001 / HR-002 / HR-003 semantics | [`docs/TRUST-MODEL.md`](docs/TRUST-MODEL.md) |
| Approved target architecture | [`docs/PLATFORM-CONCEPT.md`](docs/PLATFORM-CONCEPT.md) |
| Installation, startup, commissioning, verification, and recovery | [`docs/OPERATIONS.md`](docs/OPERATIONS.md) |
| Module-specific durable contracts | `docs/*-MODULE-PRODUCT-SPEC.md` |

Historical `.work/changes/**` and `docs/development/**` records preserve the state/evidence of their original work. Do not use them as current product authority or rewrite them merely to match later product state.

## Current capability summary

The current platform includes:

- FastMCP enforcement and forwarding over Desktop Commander's ordinary local-development contracts;
- recoverable quarantine for delete intent;
- bounded Discover operations plus persistent registered-project code, symbol, and relationship intelligence;
- a shared Skills catalogue and normalized Provider, Tool, Discover, Skill, Operation, Readiness, Exposure, Quality, and Workflow contracts;
- capability search, description, workflow recommendation, and effect-specific long-tail dispatch;
- registered provider composition with readiness/authentication/commissioning reported separately from registration, including source-aware per-binding DBHub reads and the external Docker Hub registry connector without conflating it with local Docker Engine control;
- an advisory `review_change_with_agent` workflow using configured NVIDIA NIM or Codex CLI backends;
- provider-neutral Work Management with repository-owned GitHub Project schema/drift evidence, documentation-aware intake, pre-merge documentation readiness, post-merge reconciliation milestones, preview-first Project reconciliation, and exact registered-GitHub operations;
- a read-only KIS Control Center available through the mounted `controlcenter_*` provider and as a standalone MCP App.

Implementation does not prove live commissioning. Provider authentication, external tunnel connectivity, and other live checks are operational evidence; follow [`docs/OPERATIONS.md`](docs/OPERATIONS.md) for the current procedures.

For exact current component boundaries, provider identities, public interfaces, configuration ownership, and implementation status, use [`SPEC.md`](SPEC.md).

## Repository layout

```text
AGENTS.md                              repository instructions and documentation routing
SPEC.md                                current product and implementation boundary
docs/TRUST-MODEL.md                    trust assumptions and three hard rules
docs/PLATFORM-CONCEPT.md               approved target architecture
docs/OPERATIONS.md                     canonical operator runbook
docs/*-MODULE-PRODUCT-SPEC.md          durable scoped module contracts
settings/                              canonical JSON settings
policy/kis-mcp.policy.json             machine-readable three-rule declaration
contracts/                             versioned public and internal schemas
src/kis_mcp/                           platform implementation
tests/                                 verification and regression coverage
scripts/                               bootstrap, startup, workflow, smoke, and verification entry points
.work/changes/<change-id>/             active change record; historical after merge
.agents/skills/                        repository development procedures, not product authority
```

## Quick start

Run from `C:\Projects\kis-mcp`:

```powershell
pwsh -File .\scripts\bootstrap-python.ps1
pwsh -File .\scripts\install-desktop-commander.ps1
pwsh -File .\scripts\verify.ps1
```

Bootstrap actions that require external network access are explicit operator-supervised operations outside normal Work. Normal startup and verification use the repository's locked, contained environment.

Start the local stdio gateway:

```powershell
pwsh -File .\scripts\start.ps1
```

Start a configured ChatGPT-facing instance:

```powershell
pwsh -File .\scripts\start-chatgpt.ps1 kis-op
pwsh -File .\scripts\start-chatgpt.ps1 kis-dev
```

Run the standalone Control Center:

```powershell
C:\Projects\.kis-mcp\python-env\Scripts\python.exe -m kis_mcp.control_center
```

See [`docs/OPERATIONS.md`](docs/OPERATIONS.md) before changing provider configuration, credentials, commissioning state, tunnel setup, managed tooling, or recovery procedures.

## Development changes

Use the governed change workflow in [`AGENTS.md`](AGENTS.md) and [`docs/OPERATIONS.md`](docs/OPERATIONS.md). Active implementation or documentation slices live under `.work/changes/<change-id>/` and their dedicated worktrees. After merge, those records are evidence; durable product/operations consequences belong in their canonical documents.

## Verification

Run the canonical repository gate:

```powershell
pwsh -File .\scripts\verify.ps1
```

Repository verification covers the implemented policy, provider contracts, quarantine, Discover, capability composition, Skills, providers, workflows, advisory review, Control Center, configuration, architecture boundaries, governance claims, line endings, and the full Python test suite. Live external commissioning remains separate supervised evidence.
