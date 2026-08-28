# Setup and Installation

> Operator runbook subordinate to [Operations](../OPERATIONS.md). Current architecture and deployment boundaries belong to [SPEC.md](../../SPEC.md); executable values belong to settings, scripts, contracts, source, and tests.

## Prerequisites

- Windows with PowerShell.
- Python and `uv` versions accepted by the repository bootstrap/locked project metadata.
- Node.js and npm versions accepted by the Desktop Commander installer/package metadata.
- Direct operator supervision for bootstrap, acquisition, scanning, and upgrades.

## Deployment model

Operate `kis-mcp` from the repository checkout at `C:\Projects\kis-mcp`. Use [`../../settings/kis-mcp.settings.json`](../../settings/kis-mcp.settings.json) and [`../../policy/kis-mcp.policy.json`](../../policy/kis-mcp.policy.json) as executable configuration/policy inputs; use [SPEC.md](../../SPEC.md) for the supported product/deployment boundary.

## Generated state

Generated runtime state is not repository authority and must not be committed. Resolve current state/quarantine/provider/tool paths from the applicable settings and runtime status instead of relying on a copied directory tree.

If derived project recovery state must be reconstructed, quarantine the affected generated path through the normal KIS quarantine operation and rerun the eligible operation. Never convert generated state into tracked project configuration.

## Install Python dependencies

Run the supervised bootstrap:

```powershell
pwsh -File .\scripts\bootstrap-python.ps1
```

Bootstrap may use external network access. Normal startup and verification use the locked external environment and do not perform dependency resolution as a substitute for bootstrap.

## Install Desktop Commander

Use the exact archive identity currently declared under `desktop_commander` in [`../../settings/kis-mcp.settings.json`](../../settings/kis-mcp.settings.json). Archive acquisition and security scanning are explicit supervised actions outside normal Work.

Prepare the project-local dependency cache, then run the offline installer:

```powershell
pwsh -File .\scripts\prepare-desktop-commander-cache.ps1
pwsh -File .\scripts\install-desktop-commander.ps1
```

Do not remove the installer's offline/script-suppression controls to make a failed install succeed. If archive identity, digest, package identity, dependency closure, or scanning fails, correct the supervised acquisition/cache input and retry.

## Install managed AgentSys and agnix tooling

Install the optional pinned host tools through their repository scripts. Agnix requires WSL2 with the configured Ubuntu distribution available; its supervised bootstrap downloads the exact upstream Linux release asset, verifies the published SHA-256 sidecar, smoke-tests the binary through WSL, and then promotes it into KIS-generated tooling under `C:\Projects\.kis-mcp\tools`.

```powershell
pwsh -NoProfile -File .\scripts\install-agentsys.ps1
pwsh -NoProfile -File .\scripts\install-agnix.ps1
```

The agnix runtime does not depend on Node/npm. Do not substitute the upstream Windows `agnix-binary.exe` when Smart App Control blocks it, and do not use Defender exclusions or file relocation as a trust workaround.

Start a managed AgentSys host with the intended platform selector:

```powershell
pwsh -NoProfile -File .\scripts\start-agentsys-host.ps1 -Platform claude
pwsh -NoProfile -File .\scripts\start-agentsys-host.ps1 -Platform opencode
pwsh -NoProfile -File .\scripts\start-agentsys-host.ps1 -Platform codex
```

Use the scripts/settings/source for exact installed versions, paths, supported surfaces, and validation behavior. Historical bootstrap evidence under `docs/development/bootstrap/**` is investigation evidence only, not current operator procedure.

## Upgrade Desktop Commander

1. Check the authoritative package release outside Work and acquire/scan that exact archive through the supervised bootstrap path.
2. Update `desktop_commander.version`, `desktop_commander.archive.file_name`, and `desktop_commander.archive.sha256` in [`../../settings/kis-mcp.settings.json`](../../settings/kis-mcp.settings.json) to one consistent release identity.
3. Prepare the verified archive's dependency cache and install offline:

   ```powershell
   pwsh -File .\scripts\prepare-desktop-commander-cache.ps1
   pwsh -File .\scripts\install-desktop-commander.ps1
   ```

4. Capture the installed provider contract:

   ```powershell
   pwsh -File .\scripts\capture-provider-contract.ps1
   ```

5. Review the contract/fingerprint diff and update only affected adapters/contracts.
6. Run the applicable focused checks and repository verification before accepting the upgrade.

Do not use `latest` during normal startup. Exact provider identity and compatibility truth belong to settings/contracts/source/tests rather than this runbook.