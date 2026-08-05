# agnix Bootstrap

## Installed boundary

agnix `0.45.0` is installed independently at:

```text
C:\Projects\.kis-mcp\tools\agnix\0.45.0
```

The verified command is:

```text
C:\Projects\.kis-mcp\tools\agnix\0.45.0\node_modules\.bin\agnix.cmd
```

Run it directly, for example:

```powershell
C:\Projects\.kis-mcp\tools\agnix\0.45.0\node_modules\.bin\agnix.cmd --version
C:\Projects\.kis-mcp\tools\agnix\0.45.0\node_modules\.bin\agnix.cmd .
```

The npm package provides the agnix CLI. It does not contain the repository's separate native `agnix-mcp` binary, so the bootstrap records MCP status as `not_in_npm_distribution` rather than claiming an unavailable entrypoint.

## kis-mcp exposure

`settings/bootstrap/agnix.install.json` keeps direct kis-mcp exposure disabled. A later Tools adapter may mount the CLI or a separately verified native MCP binary without coupling it to AgentSys.

## Upgrade and recovery

Rerunning `scripts/install-agnix.ps1` moves the previous versioned installation into:

```text
C:\Projects\.kis-mcp\quarantine\agnix\<operation-id>
```

Installation metadata is written to the versioned installation root as `installation.json`. No credentials are stored by the bootstrap.
