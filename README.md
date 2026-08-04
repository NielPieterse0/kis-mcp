# kis-mcp

A private, operator-supervised repository platform built from a FastMCP gateway and Desktop Commander foundation.

The current implementation is the small Work-plane enforcement baseline. The approved final product model adds bounded **Discover**, **Govern**, and **Work** planes as defined in `docs/PLATFORM-CONCEPT.md`.

The gateway preserves ordinary local development tools and enforces only three prohibited intents:

1. writing outside `C:\Projects`;
2. external network operations through local Work;
3. permanent deletion instead of recoverable quarantine.

Everything else remains available through normal tooling.

## Architecture

```text
ChatGPT -> kis-mcp FastMCP boundary -> Desktop Commander -> local environment
```

Desktop Commander is installed from its authoritative package and is not vendored or forked here. Project-specific code is limited to invocation-effect resolution, the three-rule decision core, quarantine, gateway wiring, tests, and operations.

## Repository layout

```text
AGENTS.md                         repository authority
SPEC.md                           current product and implementation boundary
docs/PLATFORM-CONCEPT.md           approved final platform outcome
docs/TRUST-MODEL.md               trust model and three hard rules
docs/OPERATIONS.md                install, start, configure, verify
docs/LESSONS-APPLICABILITY.md     scoped prior-project lessons and review triggers
docs/HARD-BLOCK-APPROVAL-REGISTER.md operator approval of active HR hard blocks and quarantine decisions
docs/NON-HARD-CONTROLS.md         resolver, structural, startup, and provider controls excluded from hard-block approval
settings/kis-mcp.settings.json     runtime/provider settings
policy/kis-mcp.policy.json         exact three-rule declaration
src/kis_mcp/                       small FastMCP enforcement layer
tests/                            policy and verification baseline
scripts/                          operator bootstrap/start/verify
```

## Bootstrap
```powershell
cd C:\Projects\kis-mcp
pwsh -File .\scripts\bootstrap-python.ps1
pwsh -File .\scripts\install-desktop-commander.ps1
pwsh -File .\scripts\verify.ps1
```

The Python bootstrap may use external network access and must be performed by the operator outside the normal Work path. It generates `uv.lock` and installs the locked environment beneath `C:\Projects\.kis-mcp\python-env`.

Desktop Commander archive acquisition and security scanning are separate supervised preparation actions. The repository installer verifies the configured archive in the current user's `Downloads` directory and uses `npm.cmd --offline --ignore-scripts`; it does not download the package or fall back to the registry. The package's complete runtime dependency closure must already exist in the separately scanned project-local npm cache.

Normal startup and verification do not resolve, install, or update packages from the network.

## Start

```powershell
pwsh -File .\scripts\start.ps1
```

## Status

The greenfield authority, JSON configuration, three-rule policy core, Desktop Commander adapter, quarantine service, scripts, and tests form the initial implementation.

The locked Python environment, pinned Desktop Commander installation, provider source-contract audit, policy clean sweep, and repository verification are current. Live provider transport and end-to-end forwarding still require explicit commissioning evidence before the gateway is described as production-ready. This status does not disable Desktop Commander tools outside HR-001, HR-002, and HR-003.
