# AgentSys Bootstrap

## Installed boundary

AgentSys `6.0.1` is installed at:

```text
C:\Projects\.kis-mcp\tools\agentsys\6.0.1
```

Its complete upstream plugin catalogue is stored beneath the isolated managed home:

```text
C:\Projects\.kis-mcp\agent-hosts\agentsys
```

The bootstrap configures three independent host projections:

- Claude Code plugins: `.claude\plugins\*@agentsys`
- OpenCode commands, agents, skills, and native plugin: `.config\opencode`
- Codex skills: `.codex\skills`

No user-profile or global host configuration is modified. The installer redirects home, application-data, XDG, Claude, OpenCode, Codex, npm cache, and temporary paths beneath `C:\Projects`.

## Use

Launch a host with the managed profile:

```powershell
pwsh -NoProfile -File scripts\start-agentsys-host.ps1 -Platform claude
pwsh -NoProfile -File scripts\start-agentsys-host.ps1 -Platform opencode
pwsh -NoProfile -File scripts\start-agentsys-host.ps1 -Platform codex
```

The corresponding host executable must already be installed and available on `PATH`. The launcher prepends the managed AgentSys and agnix binary directories so workflows can resolve their local companion commands. Host authentication remains independent and is not performed by this bootstrap.

## kis-mcp command exposure

The complete distribution is installed, but kis-mcp does not automatically expose every command. `settings/bootstrap/agentsys.install.json` contains the full 25-command catalogue; an abbreviated example is:

```json
{
  "kis_mcp_command_policy": {
    "default_enabled": false,
    "available_commands": ["next-task", "repo-intel", "ship"],
    "enabled_commands": []
  }
}
```

A later generic Tools adapter will read this catalogue. Commands that fit its existing execution contract can then be enabled through JSON without adding command-specific Python code. Host-native availability and kis-mcp exposure are separate states.

## Upgrade and recovery

Rerunning `scripts/install-agentsys.ps1` moves the previous managed package and host profile into:

```text
C:\Projects\.kis-mcp\quarantine\agentsys\<operation-id>
```

The script never permanently deletes the previous installation. Installation metadata is written to `C:\Projects\.kis-mcp\agent-hosts\agentsys\installation.json`.

AgentSys workflows may invoke GitHub, deployment, browser, LLM, or other external capabilities. Installing a command does not authorize or execute those capabilities. Each invocation remains subject to the host and kis-mcp boundaries through which it is run.
