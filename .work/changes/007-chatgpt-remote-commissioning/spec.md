# Change Specification: ChatGPT Remote Commissioning

- **Change ID**: `007-chatgpt-remote-commissioning`
- **Status**: Approved for implementation by operator request
- **Risk Profile**: rigorous

## Outcome

Complete the supervised ChatGPT-facing path from a loopback FastMCP streamable HTTP endpoint through the OpenAI tunnel client to two separately configured instances: `operation` and `development`.

## Authority and scope

- Authoritative sources: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, `docs/OPERATIONS.md`, `settings/kis-mcp.settings.json`, and the proven `sdk-tool` tunnel scripts as harvest-only source material.
- The three Work rules remain unchanged. Tunnel/bootstrap traffic is an operator-supervised connector boundary, not a Desktop Commander Work invocation.
- Tunnel authentication IDs and tunnel IDs are non-secret identifiers stored directly in canonical settings.
- The tunnel client executable is configured as `C:\Tools\openai-tunnel-client\tunnel-client.exe`.

## Requirements

- **REQ-001**: Add a `remote_mcp` settings object defining loopback HTTP host/path, two instance records, active instance, tunnel profile names, tunnel IDs, tunnel authentication IDs, and the tunnel client path.
- **REQ-002**: Validate settings strictly, including loopback-only host, distinct ports/profile names/tunnel IDs, supported instance names, valid identifier shapes, and `/mcp` endpoint paths.
- **REQ-003**: Add a dedicated Python HTTP entry point that reuses `build_server()` and starts FastMCP streamable HTTP for exactly one named instance without changing local stdio startup.
- **REQ-004**: Add a PowerShell state helper that reads and validates tunnel/instance configuration from JSON.
- **REQ-005**: Add a profile setup script that initializes either instance from settings, preserves an existing profile unless explicitly backed up/replaced, and uses only the stored non-secret identifiers.
- **REQ-006**: Add a supervised launcher that starts the selected HTTP server and tunnel, verifies loopback readiness, owns both processes, and terminates both together.
- **REQ-007**: Add an explicit `-Instance operation|development` switch and default it from `active_instance`; no automatic production/development failover.
- **REQ-008**: Add a local smoke script that proves configuration, HTTP startup, MCP initialization/tool listing, and instance separation without requiring a live external tunnel.
- **REQ-009**: Document exact setup, launch, switching, ChatGPT connector selection, tunnel identifier requirements, and live smoke-test steps.
- **REQ-010**: Preserve the full standard mixed-purpose tool surface on both remote instances; omit only provider functionality whose every invocation is necessarily external-network-only.

## Acceptance

1. Given valid settings, when `python -m kis_mcp.remote_runtime --instance development` starts, then a loopback streamable HTTP MCP endpoint is available at the configured port and path.
2. Given `operation` and `development`, when their settings are loaded, then their ports and tunnel profile names are distinct and selected deterministically; stored tunnel identifiers must also be distinct.
3. Given missing tunnel identifiers, or a missing tunnel executable/profile, when setup or the supervised launcher starts, then it fails before claiming tunnel readiness with a corrective error.
4. Given the local smoke script, when run without external network access, then both instances initialize MCP, expose the same representative filesystem/edit/process surface, call `kis_health`, perform a write/read round trip, and quarantine the smoke artifact.
5. Given repository verification and the current-change scope check, when run on the final branch, then both pass without changing `policy/kis-mcp.policy.json`.

## Risks and recovery

- Wrong instance routing: prevented by strict named selection and distinct configuration checks.
- Orphaned server/tunnel processes: launcher owns both and stops the peer when either exits.
- Identifier persistence: tunnel IDs and tunnel authentication IDs are stored directly in canonical settings and reused across updates.
- Tunnel profile replacement: refused by default; explicit backup-and-replace is recoverable.
- Recovery: stop the launcher, restore prior settings/scripts from Git, and keep local stdio startup unchanged.

## Out of scope

- Creating or deleting OpenAI control-plane tunnels.
- Committing generated tunnel profile YAML.
- Automatic failover or load balancing between operation and development.
- Changing HR-001, HR-002, HR-003, Desktop Commander contracts, or provider policy behavior.
