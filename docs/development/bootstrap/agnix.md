# agnix Bootstrap

## Installed boundary

agnix `0.45.0` is installed independently at the operator-approved ignored repo-local compatibility path:

```text
C:\Projects\kis-mcp\.temp\tools\agnix\0.45.0
```

The verified wrapper and native commands are:

```text
C:\Projects\kis-mcp\.temp\tools\agnix\0.45.0\node_modules\.bin\agnix.cmd
C:\Projects\kis-mcp\.temp\tools\agnix\0.45.0\node_modules\agnix\bin\agnix-binary.exe
```

The same native executable was blocked by Windows Application Control from the prior `C:\Projects\.kis-mcp\tools\agnix\0.45.0` location and was live-smoked successfully after relocation. The former installation was retained recoverably beneath KIS quarantine.

The npm package provides the agnix CLI. It does not contain the separate native `agnix-mcp` binary, so the bootstrap records MCP status as `not_in_npm_distribution`. All configured state paths remain beneath `C:\Projects` without traversing a junction or other reparse point.

## kis-mcp exposure

Direct provider/MCP exposure remains disabled. KIS exposes only the bounded workflow operation `validate_agent_configuration`, which calls the pinned native binary through Work middleware with fixed `--format json`, target, strict, and bounded max-file arguments. It exposes no fix, watch, init, telemetry, schema, tools, arbitrary-command, or MCP passthrough authority.

## Upgrade and recovery

Rerunning `scripts/install-agnix.ps1` first installs and smoke-tests the exact package beneath the configured temporary root. Only a validated package is activated; the previous versioned installation is then retained at:

```text
C:\Projects\.kis-mcp\quarantine\agnix\<operation-id>
```

If activation fails, the new package is retained in that quarantine operation and the previous installation is restored where possible. Installation metadata is written to the versioned installation root as `installation.json`. No credentials are stored by the bootstrap.
