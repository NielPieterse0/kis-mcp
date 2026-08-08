# Startup Hardening

## Operator workflow

Tunnel control-plane credentials are stored as per-user Generic Credentials in Windows Credential Manager. Checked-in settings contain only the canonical `secret://tunnel/<instance>/authentication-token` reference; the runtime derives the non-secret Credential Manager target `kis-mcp/tunnel/<instance>` from that reference. Store or replace the selected instance's credential once before profile setup or startup:

```powershell
pwsh -File .\scripts\set-tunnel-credential.ps1 -Instance development
```

Setup and startup retrieve the secret only for the owned tunnel-client process. They do not write it to JSON, profile YAML, logs, or runtime state.

### 1. Generate or replace a tunnel profile

Profile generation is a static commissioning action. It does not require the local MCP endpoint to be running.

```powershell
pwsh -File .\scripts\setup-tunnel.ps1 -Instance development
```

Use `-BackupExistingProfile` to preserve and replace an existing profile. The selected Windows credential is validated before the active profile is moved into backup, so a missing credential leaves the existing profile in place.

```powershell
pwsh -File .\scripts\setup-tunnel.ps1 -Instance development -BackupExistingProfile
```

The script reports `live_validation=skipped` and `setup_log=<path>`. Tunnel-client initialization and doctor output are written to that local runtime log instead of the operator console. A stopped local server is not treated as an invalid tunnel profile.

### 2. Optionally validate a live endpoint

Run live validation only when the selected local MCP endpoint is already listening.

```powershell
pwsh -File .\scripts\setup-tunnel.ps1 `
  -Instance development `
  -BackupExistingProfile `
  -ValidateLiveEndpoint
```

The script polls MCP `initialize` readiness before invoking `tunnel-client doctor`.

- Endpoint refusal or timeout returns `KIS_MCP_ENDPOINT_NOT_READY`.
- A doctor failure after endpoint readiness returns `KIS_MCP_TUNNEL_PROFILE_INVALID`.

### 3. Start the supervised ChatGPT path

```powershell
pwsh -File .\scripts\start-chatgpt.ps1 -Instance development
```

The launcher performs this order:

1. reclaim only stale processes owned by the selected instance and reject unrelated ownership of its selected port;
2. start the local kis-mcp HTTP runtime directly as `python -m kis_mcp.remote_runtime --instance <name>`;
3. poll MCP `initialize` readiness;
4. retrieve the selected tunnel credential non-interactively from the current user's Credential Manager entry;
5. start the tunnel client with that credential only in the owned tunnel process environment;
6. poll the tunnel `/readyz` endpoint;
7. capture child-process stdout and stderr beneath the instance runtime root;
8. write a versioned startup-state JSON record containing the diagnostic log paths;
9. emit the bounded readiness fields below.

The peer `kis-op`/`kis-dev` instance may remain active. Normal startup does not unlock the application-managed encrypted vault and does not prompt for vault material. The remote MCP runtime honors `settings.remote_mcp.stateless_http=true`, so representative smoke calls after `initialize` do not require an MCP session ID.

```text
health=ready
endpoint=<loopback MCP endpoint>
policy_fingerprint=<sha256>
tunnel_state=ready
tunnel_profile=<profile name>
tunnel_id=<non-secret tunnel identifier>
startup_state=<local JSON state path>
```

The operator console contains only the bounded kis-mcp fields above. FastMCP, provider, server transport, tunnel-client Fx, admin UI, and startup diagnostics are retained in the log paths recorded by the startup-state JSON.

The launcher owns both child processes. Closing or interrupting the launcher stops the owned local runtime and tunnel process. It does not terminate unrelated listeners.

## Provider containment

Desktop Commander remains the authoritative Work provider and is not modified or vendored.

A kis-mcp-owned Node preload adapter is installed before the provider starts. It performs three bounded compatibility actions:

1. returns a deterministic local `{ "flags": {} }` response for the exact configured `DC_FLAG_URL` without opening a socket;
2. suppresses provider `notifications/message` records before FastMCP receives them;
3. removes provider-specific `_meta` and `meta` fields from `tools/list` responses.

All other fetch requests, JSON-RPC requests, responses, errors, provider tools, and non-log notifications pass through unchanged.

FastMCP starts with `show_banner=False`, so deployment promotion and update output are not part of the supervised runtime surface.

## Public Work surface

The startup compatibility adapter preserves all normal provider tool names and schemas, including `get_config`, `set_config_value`, `get_prompts`, `get_usage_stats`, and `get_recent_tool_calls`. It removes only provider-specific presentation metadata from the `tools/list` response.

Ordinary filesystem, editing, search, terminal, process, document, and provider-administration tools remain exposed subject only to HR-001, HR-002, and HR-003. The existing inherently network-only feedback tool and `read_file.isUrl` mode remain excluded by the established provider contract. Provider tool results are not wrapped or rewritten.

## Error classification

| Error | Meaning |
|---|---|
| `KIS_MCP_ENDPOINT_NOT_READY` | The local MCP endpoint did not become ready within the bounded wait. |
| `KIS_MCP_TUNNEL_PROFILE_INVALID` | Live endpoint readiness succeeded, but tunnel-client doctor rejected the profile or live configuration. |
| `KIS_MCP_TUNNEL_PROFILE_MISSING` | Generate the selected profile before startup. |
| `KIS_MCP_PORT_IN_USE` | The selected loopback port already has a listener. No process is terminated automatically. |
| `KIS_MCP_OTHER_INSTANCE_ACTIVE` | The alternate supervised instance is already listening. |
| `KIS_MCP_TUNNEL_NOT_READY` | The tunnel process started but did not report ready before the deadline. |

## Recovery

Revert the startup-hardening change to restore the previous scripts and provider launch behavior. Existing profile YAML is never permanently deleted: replacement requires `-BackupExistingProfile`, which moves the prior profile beneath the profile backup directory. The Windows Credential Manager entry remains operator-owned and is not copied, logged, or deleted by rollback.
