# Change Specification: Agent Tooling Bootstrap

- **Change ID**: `031-agent-tooling-bootstrap`
- **Status**: Approved for implementation
- **Risk Profile**: rigorous
- **Development level**: Complex — supervised external package installation, three host-specific configuration surfaces, executable discovery, and strict write-boundary containment.

## Outcome

Install the complete pinned AgentSys `6.0.1` distribution and agnix `0.45.0` independently beneath `C:\Projects\.kis-mcp`, configure AgentSys for Claude Code, OpenCode, and Codex using isolated managed host profiles, and leave future kis-mcp command exposure controlled by JSON rather than command-specific Python implementation.

## Authority and scope

- Authoritative sources: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, upstream AgentSys and agnix package contracts, and the operator direction in this conversation.
- Owned paths: the paths declared in `scope.json`.
- Shared paths: none.
- Excluded paths: `src/kis_mcp/tools/**`, `tests/tools/**`, `settings/tools/**`, `contracts/tools/**`, `src/kis_mcp/server.py`, Providers, Discover, Skills, and policy implementation.
- Dependencies: Node.js 18+, npm, PowerShell 7, Git, installed Claude Code/OpenCode/Codex commands when launching managed profiles.
- Integration owner: a later Tools integration slice after `029-tools-code-tooling` merges.

## Architecture

AgentSys and agnix remain independent installations:

```text
C:\Projects\.kis-mcp\tools\
├── agentsys\6.0.1\
└── agnix\0.45.0\

C:\Projects\.kis-mcp\agent-hosts\agentsys\
├── .claude\
├── .config\opencode\
└── .codex\
```

The AgentSys installer runs once with all three supported targets while `HOME`, `USERPROFILE`, `APPDATA`, `LOCALAPPDATA`, `XDG_CONFIG_HOME`, `CLAUDE_CONFIG_DIR`, `OPENCODE_CONFIG_DIR`, and `CODEX_HOME` are redirected beneath the managed host root. A launcher restores the same environment before invoking each host. agnix is installed separately and verified through both CLI and MCP entrypoints where the npm package provides them.

Installation does not mount either component into kis-mcp. Future command exposure will consume a JSON catalogue with default-deny enablement; adding an upstream command must require JSON only when its execution contract fits an existing generic command adapter.

## Requirements

- **REQ-001**: Pin AgentSys exactly to `6.0.1` and agnix exactly to `0.45.0`; reject `latest`, ranges, and unpinned package specifications.
- **REQ-002**: Install each distribution into a separate versioned root below `C:\Projects\.kis-mcp\tools`.
- **REQ-003**: Configure AgentSys completely for `claude`, `opencode`, and `codex` in one supervised bootstrap operation.
- **REQ-004**: Every explicit or redirected installation, cache, temporary, configuration, state, and log path must resolve beneath `C:\Projects`.
- **REQ-005**: Do not persist credentials, API keys, authentication tokens, or host auth files in repository content.
- **REQ-006**: Preserve replaced installations and generated profiles recoverably; do not use permanent-delete commands.
- **REQ-007**: Provide one launcher that applies the managed environment and invokes Claude Code, OpenCode, or Codex without changing global user configuration.
- **REQ-008**: Record deterministic non-secret installation metadata, executable locations, versions, configured hosts, and readiness in JSON.
- **REQ-009**: Keep AgentSys command availability distinct from kis-mcp exposure. The complete host installation may contain all upstream commands, while the future kis-mcp command catalogue remains disabled by default and policy-driven.
- **REQ-010**: Do not modify the active Tools-module worktree or claim that AgentSys is an MCP server. agnix may be recorded as an MCP-capable tool independently.
- **REQ-011**: Tests must inspect scripts and settings without performing network operations or depending on existing host authentication.
- **REQ-012**: Installation must fail correctively when a command, package artifact, required executable, or managed path cannot be verified.

## Acceptance

1. **Given** a clean managed state root, **When** `install-agentsys.ps1` runs, **Then** AgentSys `6.0.1` is installed and its installer configures Claude Code, OpenCode, and Codex only beneath the managed host root.
2. **Given** a clean managed state root, **When** `install-agnix.ps1` runs, **Then** agnix `0.45.0` is installed independently and its CLI and available MCP entrypoint report readiness.
3. **Given** any generated path, **When** the installer validates it, **Then** `C:\Projects-old` and every other prefix collision or outside path is rejected.
4. **Given** an installed host profile, **When** the launcher selects `claude`, `opencode`, or `codex`, **Then** it applies only managed environment variables and invokes the corresponding existing host executable.
5. **Given** repository tests, **When** the bootstrap suite runs, **Then** exact pins, independent roots, three-host configuration, no permanent deletion, no secret persistence, and default-deny future exposure are proven.
6. **Given** the active parallel changes, **When** scope validation runs, **Then** no path overlaps change `029-tools-code-tooling` or other active slices.

## Risks and recovery

- Risk: the upstream installer assumes user-profile paths. Mitigation: redirect every relevant home/config variable, inspect resulting paths, and reject any outside-path evidence.
- Risk: AgentSys plugins execute external commands or require host authentication. Mitigation: installation and host configuration are separate from command execution; no workflow is run during commissioning.
- Risk: package contents or entrypoints drift. Mitigation: exact versions, package metadata verification, executable smoke checks, and a new slice for upgrades.
- Recovery: stop using the managed launcher and move the versioned installation or host profile to `C:\Projects\.kis-mcp\quarantine`; global host configuration remains untouched.

## Out of scope

- Mounting AgentSys or agnix into `build_server()`.
- Implementing the generic policy-driven command adapter owned by the Tools module.
- Selecting the first kis-mcp-exposed AgentSys commands.
- Authenticating Claude Code, OpenCode providers, Codex, GitHub CLI, or any external service.
- Running AgentSys workflows against a repository during installation.
