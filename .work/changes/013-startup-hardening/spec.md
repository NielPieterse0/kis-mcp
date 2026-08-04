# Startup Hardening Specification

## Approved outcome

Make supervised ChatGPT startup deterministic and appliance-like while preserving the existing Work architecture and exactly HR-001, HR-002, and HR-003.

## Root causes

1. `setup-tunnel.ps1` couples profile creation to a live MCP endpoint through `tunnel-client doctor`; a stopped server is therefore mislabeled as an invalid profile.
2. Desktop Commander 0.2.46 emits buffered `notifications/message` records whose scalar `data` values trigger a FastMCP proxy validation defect and leak provider startup details through the gateway.
3. Desktop Commander initializes feature flags unconditionally and attempts the configured URL even when pointed at a failing loopback endpoint.
4. FastMCP HTTP startup intentionally displays a banner and version/deployment notices that are unnecessary for an operator-supervised appliance.
5. Provider administration and UI-oriented tools remain visible even though kis-mcp owns provider configuration and the ChatGPT surface does not need those provider internals.

## Required behavior

### Tunnel commissioning

- `setup-tunnel.ps1` creates or replaces a profile and validates static generated artifacts only.
- Live endpoint validation is optional and explicit through `-ValidateLiveEndpoint`.
- A refused or unavailable local MCP endpoint reports `KIS_MCP_ENDPOINT_NOT_READY` and never `KIS_MCP_TUNNEL_PROFILE_INVALID`.
- `start-chatgpt.ps1` always starts the local MCP server first, polls MCP initialization readiness, then starts and polls the tunnel client.
- Startup success output contains only local endpoint, policy fingerprint, tunnel profile/ID, tunnel readiness, and startup-state location.

### Tunnel credential handling

- Tunnel secrets are stored as per-user Generic Credentials in Windows Credential Manager.
- Checked-in JSON stores only the non-secret `tunnel_credential_target` and explicit `configured` state.
- Setup and startup retrieve the selected secret only when needed, inject it into the owned tunnel-client process environment, and clear temporary PowerShell references after process creation.
- Credential values must not be written to repository files, generated profile YAML, logs, runtime-state JSON, or backups.
- Missing or invalid credential targets and missing credentials fail closed with specific `KIS_MCP_TUNNEL_CREDENTIAL_*` errors.

### Provider containment

- A project-owned Node preload adapter is installed before Desktop Commander starts.
- For the exact configured `DC_FLAG_URL`, `fetch()` returns a deterministic local `{ "flags": {} }` response without opening a socket.
- JSON-RPC `notifications/message` emitted by Desktop Commander are suppressed before FastMCP receives them.
- Provider-specific `_meta` and `meta` fields and the five approved provider administration tools are removed from `tools/list` before FastMCP constructs the proxy catalogue.
- Requests, responses, errors, ordinary tools, and non-log notifications remain unchanged.
- Desktop Commander remains authoritative and unmodified on disk; the adapter is a bounded compatibility layer for the pinned provider version.
- Compatibility behavior must not be added to Work middleware or the Desktop Commander effect resolver.

### Public surface

- Hide provider-only administration and UI tools: `get_config`, `set_config_value`, `get_prompts`, `get_usage_stats`, and `get_recent_tool_calls`.
- Continue hiding `give_feedback_to_desktop_commander` and the `read_file.isUrl` mode.
- Preserve ordinary filesystem, editing, search, terminal, process, and document tool contracts and results.
- Do not wrap every provider result in a new envelope because that would break the preserved provider contract. Gateway-owned `kis_*` tools and startup diagnostics remain kis-mcp-owned records.

### Runtime output

- HTTP startup uses `show_banner=False`.
- No FastMCP promotional or upgrade banner is emitted by the runtime.
- Provider log notifications do not reach ChatGPT.

### Ownership and base

- Change `007-chatgpt-remote-commissioning` is closed and no longer owns further startup corrections.
- Change `013-startup-hardening` exclusively owns the startup paths declared in its `scope.json`.
- Other active worktrees, including Skills, are out of scope and must not be changed.
- The final branch history is linear from exact base `0915bfa67e4452240d2c5fef677670c0c68386c7`.

## Acceptance criteria

1. Unit tests prove the startup adapter blocks exact feature-flag fetches without calling the original fetch and passes unrelated fetches through.
2. Unit tests prove scalar and structured Desktop Commander logging notifications are suppressed while ordinary JSON-RPC messages pass unchanged.
3. Provider launch tests prove both the atomic state adapter and startup adapter are preloaded in deterministic order.
4. Tunnel script tests prove setup does not call live doctor by default, optional live validation emits `KIS_MCP_ENDPOINT_NOT_READY`, and startup sequencing remains server-before-tunnel.
5. Remote runtime tests prove `show_banner=False`.
6. Startup-adapter tests prove the five provider administration tools and provider UI metadata are absent before FastMCP constructs the proxy, while representative ordinary tools remain unchanged.
7. Architecture tests prove startup compatibility behavior is absent from Work middleware and the Desktop Commander effect resolver.
8. Full locked verification and change-scope validation pass.
9. Live startup is attempted with the operator-provided identifiers. Any external tunnel limitation is reported precisely without claiming profile invalidity.
10. Credential tests prove non-secret per-instance target names, removal of superseded identifier fields, Windows Credential Manager retrieval, and no secret persistence in JSON, profile content, logs, or startup state.

## Exclusions

- No provider upgrade or fork.
- No changes to policy JSON or the three-rule resolver.
- No Discover, Skills, GitHub provider, Supabase provider, quarantine, or command-policy work.
- No automatic process termination for occupied ports.
- No credential logging or committed generated tunnel profiles.

## Recovery

Revert the branch. Generated profiles and backups remain beneath `C:\Projects\.kis-mcp\tunnel-client`; no permanent deletion is introduced.
