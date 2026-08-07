# kis-mcp

`kis-mcp` is a private, operator-supervised repository platform built on FastMCP and the authoritative Desktop Commander distribution.

The current platform provides ordinary local development operations, bounded repository discovery, reusable Skills, explicit Provider and Tool composition, a normalized capability catalogue, readiness-aware progressive exposure, first-class workflow recommendations, an optional advisory code-review agent, provider-neutral multi-project work management, and a read-only Control Center available through the gateway and as a standalone app. The approved target architecture still adds broader Govern-plane enforcement and additional executable workflow composition as defined in [`docs/PLATFORM-CONCEPT.md`](docs/PLATFORM-CONCEPT.md).

The Work path enforces exactly three prohibited outcomes:

1. writing outside `C:\Projects`;
2. external network access through local Work;
3. permanent deletion instead of recoverable quarantine.

No readiness, profile, catalogue, provider, review, score, workflow, or uncertainty state creates another Work restriction.

## Current architecture

```text
ChatGPT or local MCP client
        |
        v
kis-mcp FastMCP gateway
|- curated direct profile for frequent Work and Discover operations
|- capability search, description, and workflow recommendation
|- effect-specific read/change/external long-tail dispatch
|- instance-scoped provider readiness and exposure planning
|- runtime-scoped authenticated provider clients
|- Skills catalogue with category and capability metadata
|- optional namespaced GitHub and Supabase provider operations
|- optional project-management inventory, reconciliation, evidence, status, and traceability workflows
|- read-only KIS Control Center resource
`- review_change_with_agent
        |- NVIDIA NIM backend
        `- Codex CLI backend

Standalone read-only MCP App
`- KIS Control Center using the same local evidence model

Managed host tooling, not mounted into the gateway
|- AgentSys 6.0.1 profiles for Claude Code, OpenCode, and Codex
`- agnix 0.45.0 CLI
```

Desktop Commander is installed from its authoritative package and is not vendored or forked. Discover, Skills, Providers, Tools, workflows, capability composition, and the Control Center are implemented natively under `src/kis_mcp`.

## Capability status

| State | Capabilities |
|---|---|
| Direct gateway profile | Frequently used Work operations; `kis_health`; `kis_provider_status`; `inspect_project`; working-tree `inspect_change`; `review_change_with_agent` when ready; capability search, description, and workflow recommendation; effect-specific long-tail dispatch; and the Control Center resource. |
| Discoverable long tail | Remaining valid Desktop Commander, Skills, internal Discover, quarantine, and mounted provider operations. These remain registered and schema-validated but do not all consume the default `tools/list` context. |
| Status-only | Disabled, unavailable, authentication-gated, build-failed, or mount-failed operations remain visible in provider and capability status but are not recommended or dispatched. |
| Standalone | KIS Control Center read-only MCP App and UI resource using the same evidence model. |
| Managed host tooling | AgentSys `6.0.1` host profiles and agnix `0.45.0` CLI are installed through separate supervised bootstrap scripts. They are not mounted into the gateway or automatically authorized to run external workflows. |
| Target | Govern operations, broader semantic and trusted remote evidence, and executable orchestration for additional composed workflows. |

Implementation does not prove commissioning. GitHub requires authentication before live operations. Supabase requires project initialization or project scope, then authentication. NVIDIA NIM requires `NVIDIA_API_KEY`. Codex CLI requires an installed and authenticated `codex` executable. The two remote HTTP instances have distinct configured tunnel IDs, but configuration alone does not prove stored credentials, generated profiles, ChatGPT tool discovery, or live end-to-end commissioning.

### Provider authentication and repository routing

Provider authentication is owned by the running `kis-op` process, not by a repository or GitHub Project. The provider-neutral client lifecycle keeps one re-entrant FastMCP client connected for the parent server lifespan and permits provider-specific startup calls. GitHub uses that seam to call `get_me` when the provider starts, keep one official GitHub MCP subprocess alive across downstream sessions, and close it only when `kis-op` stops. Because the official local GitHub provider keeps its OAuth token in process memory, one new login is expected after each `kis-op` restart; ordinary tool calls during the same run reuse the authenticated process.

`settings/providers/github-mcp.provider.json` contains only provider identity, pinned executable, OAuth mode, PAT conflict metadata, and toolsets. Repository identity and GitHub Project bindings are repository-local in `settings/kis-repository.settings.json`. The repository root is derived from the checkout containing that file, `github_repository` is checked against the local `origin` remote when available, every GitHub repository operation must carry explicit repository arguments, and `gh_projects` limits Project operations for the selected repository. Changing selected repository context does not recreate the authenticated provider client.

## Repository layout

```text
AGENTS.md                              repository authority and workflow
SPEC.md                                current product and implementation boundary
docs/PLATFORM-CONCEPT.md               approved target architecture
docs/DISCOVER-MODULE-PRODUCT-SPEC.md   Discover module authority and roadmap
docs/PROVIDER-MODULE-PRODUCT-SPEC.md   Provider module contracts and current state
docs/SKILLS-MODULE-PRODUCT-SPEC.md     Skills module contracts
docs/TRUST-MODEL.md                    trust model and three hard rules
docs/OPERATIONS.md                     install, configure, operate, and verify
docs/LESSONS-APPLICABILITY.md          prior-project lessons mapped to current state
settings/kis-repository.settings.json  repository identity and GitHub Project bindings
settings/                              canonical JSON settings, including capability scoring and exposure
policy/kis-mcp.policy.json             exact three-rule declaration
contracts/                             versioned public and internal schemas
src/kis_mcp/                           platform implementation
tests/                                 policy, module, provider, capability, and integration tests
scripts/                               operator bootstrap, startup, smoke, and verification
```

Historical `.work/changes/**` and `docs/development/**` files record the state of their original slices. Use the authority documents above for current product guidance.

## Bootstrap

Run from `C:\Projects\kis-mcp`:

```powershell
pwsh -File .\scripts\bootstrap-python.ps1
pwsh -File .\scripts\install-desktop-commander.ps1
pwsh -File .\scripts\verify.ps1
```

Python dependency acquisition and Desktop Commander cache preparation are explicit operator-supervised network stages outside normal Work. Normal startup and verification use the locked external environment and do not resolve, install, or update packages from the network.

## Optional managed host tooling

AgentSys and agnix are separate supervised bootstrap components. Their installers use the network during explicit setup, install only beneath `C:\Projects`, retain replaced state under quarantine, and do not mount either component into the primary gateway.

```powershell
pwsh -NoProfile -File .\scripts\install-agentsys.ps1
pwsh -NoProfile -File .\scripts\install-agnix.ps1
```

Use [`docs/development/bootstrap/agentsys.md`](docs/development/bootstrap/agentsys.md) and [`docs/development/bootstrap/agnix.md`](docs/development/bootstrap/agnix.md) for host profiles, launch commands, status limits, and recovery.

## Start

Start the local stdio gateway:

```powershell
pwsh -File .\scripts\start.ps1
```

Start a configured ChatGPT-facing instance:

```powershell
pwsh -File .\scripts\start-chatgpt.ps1 -Instance development
```

Run the standalone read-only Control Center:

```powershell
C:\Projects\.kis-mcp\python-env\Scripts\python.exe -m kis_mcp.control_center
```

See [`docs/OPERATIONS.md`](docs/OPERATIONS.md) for installation prerequisites, capability discovery and dispatch, provider onboarding, tunnel setup, agent configuration, smoke testing, recovery, and troubleshooting.

## Discover boundary

`inspect_project` returns bounded deterministic repository, language, framework, manifest, instruction, contract, local Git, verification-discovery, Python-structure, evidence, confidence, truncation, and handoff records.

The direct `inspect_change` operation currently accepts a project path and inspects the working tree. Internal contracts and registered long-tail operations also support staged, commit, range, and branch targets, context brokering, impact analysis, and contract intelligence. These are discoverable but are not added to the direct profile by default.

Discover does not execute repository code, tests, builds, or discovered commands. It performs no network requests. Structural failures use `DISCOVER_*` errors rather than HR policy codes.

## Work management

P0-P5 work management is implemented under `src/kis_mcp/work_management` with strict settings in `settings/work-management/github-projects.settings.json`. It provides typed records, traceability, review evidence, atomic persistence, deterministic reconciliation, portfolio status, fixed-shape CLI/CI, and five task-level platform workflows.

The checked-in configuration is disabled by default. Enable it only after assigning a valid GitHub Project number and completing supervised OAuth commissioning. Reconciliation defaults to preview; apply requires an idempotency key. The GitHub adapter permits only bounded issue or pull-request addition and Project-field updates, performs revision checks and source-record deduplication, and exposes no delete or unrestricted GraphQL operation. Provider authentication remains profile-wide, while the selected repository's `gh_projects` entries are an additional routing boundary that work-management calls cannot widen.

Use the local CLI for validation and read-only planning:

```powershell
pwsh -NoProfile -File .\scripts\project-workflow.ps1 settings --settings settings\work-management\github-projects.settings.json
pwsh -NoProfile -File .\scripts\project-workflow.ps1 reconcile --desired .\desired.json --observed .\observed.json --supported-field Status
pwsh -NoProfile -File .\scripts\project-workflow.ps1 verify-traceability --trace .\trace.json --stage active
```

## Verification

Run the canonical repository gate:

```powershell
pwsh -File .\scripts\verify.ps1
```

Verification covers the three-rule policy, Desktop Commander contract and containment, quarantine and restoration, Discover, capability contracts and scoring, Skills metadata, instance-scoped Provider runtime composition, runtime-scoped provider client lifecycle, progressive exposure, workflow descriptors, the advisory agent, Control Center, architecture boundaries, configuration, governance claims, line endings, and the full Python test suite. Live provider authentication, external tunnel connectivity, and ChatGPT commissioning require separate supervised smoke evidence.
