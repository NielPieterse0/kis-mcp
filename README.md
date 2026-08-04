# kis-mcp

A private, operator-supervised repository platform built from a FastMCP gateway and Desktop Commander foundation.

The current implementation includes the Work-plane enforcement baseline and the first bounded read-only Discover capability. The approved final product model adds broader **Discover**, **Govern**, and **Work** planes as defined in `docs/PLATFORM-CONCEPT.md`.

The gateway preserves ordinary local development tools and enforces only three prohibited intents:

1. writing outside `C:\Projects`;
2. external network operations through local Work;
3. permanent deletion instead of recoverable quarantine.

Everything else remains available through normal tooling.

## Architecture

```text
ChatGPT
   |
   v
kis-mcp FastMCP platform
   +-- inspect_project -> bounded local Discover evidence
   +-- gateway tools
   +-- Desktop Commander -> ordinary local Work operations
```

Desktop Commander is installed from its authoritative package and is not vendored or forked here. Discover is implemented natively under `src/kis_mcp/discover`; `sdk-tool`, `dev-intel-tool`, and `mcp-tool` are documented source donors only and are not runtime dependencies.

## Repository layout

```text
AGENTS.md                         repository authority
SPEC.md                           current product and implementation boundary
docs/PLATFORM-CONCEPT.md          approved final platform outcome
docs/DISCOVER-MODULE-PRODUCT-SPEC.md Discover target specification and roadmap
docs/TRUST-MODEL.md               trust model and three hard rules
docs/OPERATIONS.md                install, start, configure, verify
docs/LESSONS-APPLICABILITY.md     scoped prior-project lessons and review triggers
docs/HARD-BLOCK-APPROVAL-REGISTER.md operator approval of active HR hard blocks and quarantine decisions
docs/NON-HARD-CONTROLS.md         resolver, structural, startup, and provider controls excluded from hard-block approval
settings/kis-mcp.settings.json     runtime, provider, remote, and Discover settings
policy/kis-mcp.policy.json         exact three-rule declaration
contracts/discover/                versioned inspect_project schemas
src/kis_mcp/                       FastMCP platform implementation
tests/                             policy, provider, Discover, and verification suites
scripts/                           operator bootstrap/start/verify
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

## Discover

The public `inspect_project` tool accepts a project path beneath `C:\Projects` and optional request limits that may only narrow configured maxima. It returns deterministic repository, language, manifest, instruction, contract, local Git, verification-discovery, Python-structure, evidence, confidence, truncation, and handoff records.

All limits, exclusions, allowed text types, encodings, and hard-link handling are defined under `settings.discover` in `settings/kis-mcp.settings.json`. Discover does not execute repository code, tests, builds, or discovered commands, and it performs no network requests. Structural failures use `DISCOVER_*` errors rather than HR policy codes.

## Status

The repository authority, JSON configuration, three-rule policy core, Desktop Commander adapter, quarantine service, provider module, local/HTTP launch paths, and bounded Discover foundation are implemented and covered by the locked verification suite.

Fresh local HTTP smoke verification passed on both `operation` and `development`: each exposed 30 tools, executed `inspect_project`, health, representative read/write/edit/process calls, and recoverable quarantine, while the network-only feedback tool remained absent. External tunnel commissioning still requires operator-supplied tunnel configuration. None of these status statements disable tools outside HR-001, HR-002, and HR-003.
