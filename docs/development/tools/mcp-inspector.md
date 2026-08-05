# MCP Inspector

## Status

MCP Inspector is installed as operator-supervised support tooling. It is not mounted into the kis-mcp gateway, Providers module, or public Tools catalogue.

The managed dependency is pinned to:

- package: `@modelcontextprotocol/inspector`
- version: `2.0.0`
- minimum Node.js: `22.19.0`
- install root: `C:\Projects\.kis-mcp\tools\mcp-inspector\2.0.0`

All managed package, home, cache, temporary, log, storage, and quarantine paths remain beneath `C:\Projects`.

## Install or refresh

Run the supervised bootstrap command from the repository root:

```powershell
pwsh -NoProfile -File .\scripts\install-mcp-inspector.ps1
```

The installer may access npm. It stages the exact package version, verifies package identity and the published launcher, runs `--cli --help`, and only then activates the package. An existing installation is moved into recoverable quarantine before replacement. The installer never permanently deletes artifacts.

## Launch

The selected kis-mcp HTTP instance must already be running.

Development instance:

```powershell
pwsh -NoProfile -File .\scripts\start-mcp-inspector.ps1 -Instance development
```

Operation instance without opening a browser automatically:

```powershell
pwsh -NoProfile -File .\scripts\start-mcp-inspector.ps1 -Instance operation -NoBrowser
```

The launcher reads the selected target port from `settings/kis-mcp.settings.json`, binds Inspector to `127.0.0.1`, and supplies a non-persistent ad-hoc local `/mcp` target. Inspector can invoke the tools exposed by that target, including mutation-capable tools, subject to normal kis-mcp policy and approval. Default Inspector UI ports are:

- operation: `6274`
- development: `6275`

Inspector runtime state is separated by kis-mcp instance beneath `C:\Projects\.kis-mcp\mcp-inspector`.

## Boundaries

- No gateway or provider registration is added.
- No automatic startup or update occurs.
- No arbitrary remote URL is exposed through Work.
- Installation network access occurs only when the operator runs the installer.
- Normal launch uses only the already installed local package.
- The managed launcher supplies only the selected local HTTP target; direct upstream Inspector invocation may expose other supported target modes.

## Recovery

Installer replacement state is retained beneath:

```text
C:\Projects\.kis-mcp\quarantine\mcp-inspector\<operation-id>\
```

A failed activation attempts to move the failed new package into `failed-new-package` and restore `previous-package`. Recovery can also be performed by rerunning the installer or manually restoring a quarantined package.

## Verification

The change includes structural tests for exact dependency identity, containment, staging, smoke-before-activation ordering, quarantine and rollback, instance selection, local binding, and managed runtime state.

Commissioning evidence on August 5, 2026:

- Node.js `v22.23.1` satisfied the upstream minimum.
- `@modelcontextprotocol/inspector@2.0.0` installed successfully.
- The Inspector CLI help smoke passed before activation.
- Inspector CLI connected to the development kis-mcp endpoint at `http://127.0.0.1:8011/mcp` and returned its tool catalogue.
- A replacement install quarantined both the previous package and the isolated bootstrap home without leaving per-install temp residue.
- The managed development launcher served HTTP 200 at `http://127.0.0.1:6275/`; its ephemeral local auth token was redacted from stored smoke evidence.
