# kis-mcp

`kis-mcp` is a private, operator-supervised repository platform built on FastMCP and the authoritative Desktop Commander distribution.

The current platform provides ordinary local development operations, bounded repository discovery, reusable Skills, explicit provider composition, an optional advisory code-review agent, and a standalone read-only Control Center. The approved target architecture adds a Govern plane and broader workflow composition as defined in [`docs/PLATFORM-CONCEPT.md`](docs/PLATFORM-CONCEPT.md).

The Work path enforces exactly three prohibited outcomes:

1. writing outside `C:\Projects`;
2. external network access through local Work;
3. permanent deletion instead of recoverable quarantine.

No readiness, profile, catalogue, provider, review, or uncertainty state creates another Work restriction.

## Current architecture

```text
ChatGPT or local MCP client
        |
        v
kis-mcp FastMCP gateway
├── Desktop Commander Work tools
├── five gateway operations
├── Discover: inspect_project and inspect_change
├── Skills: nine catalogue and mutation operations
├── optional namespaced GitHub and Supabase provider tools
└── review_change_with_agent
        ├── NVIDIA NIM backend
        └── Codex CLI backend

Standalone read-only MCP App
└── KIS Control Center
```

Desktop Commander is installed from its authoritative package and is not vendored or forked. Discover, Skills, Providers, Tools, workflows, and the Control Center are implemented natively under `src/kis_mcp`.

## Capability status

| State | Capabilities |
|---|---|
| Public gateway | Desktop Commander Work surface; `kis_health`; provider status; quarantine list, move, and restore; `inspect_project`; working-tree `inspect_change`; nine Skills operations; `review_change_with_agent`; namespaced GitHub and Supabase tools when their adapters mount successfully. |
| Internal, not public gateway tools | Commit, range, branch, and staged change readers; context brokering; impact analysis; contract intelligence; explicit project cataloging; provider-admission evidence. |
| Standalone | KIS Control Center read-only MCP App and UI resource. |
| Target | Govern operations, public context and impact workflows, broader semantic and remote evidence, and composed platform workflows. |

Implementation does not prove commissioning. GitHub requires authentication before live operations. Supabase requires project initialization or project scope, then authentication. NVIDIA NIM requires `NVIDIA_API_KEY`. Codex CLI requires an installed and authenticated `codex` executable. The two remote HTTP instances have distinct configured tunnel IDs, but configuration alone does not prove stored credentials, generated profiles, ChatGPT tool discovery, or live end-to-end commissioning.

## Repository layout

```text
AGENTS.md                              repository authority and workflow
SPEC.md                                current product and implementation boundary
docs/PLATFORM-CONCEPT.md               approved target architecture
docs/DISCOVER-MODULE-PRODUCT-SPEC.md   Discover module authority and roadmap
docs/PROVIDER-MODULE-PRODUCT-SPEC.md   Provider module contracts and current state
docs/SKILLS-MODULE-PRODUCT-SPEC.md     Skills module contracts
docs/TRUST-MODEL.md                    trust model and three hard rules
docs/OPERATIONS.md                     install, configure, start, and verify
docs/LESSONS-APPLICABILITY.md          prior-project lessons mapped to current state
settings/                              canonical JSON settings
policy/kis-mcp.policy.json             exact three-rule declaration
contracts/                             versioned public and internal schemas
src/kis_mcp/                           platform implementation
tests/                                 policy, module, provider, and integration tests
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

See [`docs/OPERATIONS.md`](docs/OPERATIONS.md) for installation prerequisites, provider onboarding, tunnel setup, agent configuration, smoke testing, recovery, and troubleshooting.

## Discover boundary

`inspect_project` returns bounded deterministic repository, language, framework, manifest, instruction, contract, local Git, verification-discovery, Python-structure, evidence, confidence, truncation, and handoff records.

The public `inspect_change` operation currently accepts a project path and inspects the working tree. Internal contracts and readers also support staged, commit, range, and branch targets, but those target selectors are not exposed by the current public tool signature.

Discover does not execute repository code, tests, builds, or discovered commands. It performs no network requests. Structural failures use `DISCOVER_*` errors rather than HR policy codes.

## Verification

Run the canonical repository gate:

```powershell
pwsh -File .\scripts\verify.ps1
```

Verification covers the three-rule policy, Desktop Commander contract and containment, quarantine and restoration, Discover, Skills, Provider runtime composition, the advisory agent, Control Center, configuration, governance claims, line endings, and the full Python test suite. Live provider authentication, external tunnel connectivity, and ChatGPT commissioning require separate supervised smoke evidence.
