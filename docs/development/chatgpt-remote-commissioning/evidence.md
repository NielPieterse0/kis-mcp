# ChatGPT Remote Commissioning Evidence

## Scope

This record covers the local ChatGPT-compatible transport path:

```text
streamable HTTP -> kis-mcp FastMCP gateway -> Desktop Commander
```

It does not claim the external Secure MCP Tunnel or ChatGPT app hop, because the repository does not contain the real `operation` and `development` tunnel/control-plane identifiers.

## Verified configuration

- Tunnel client: `C:\Tools\openai-tunnel-client\tunnel-client.exe`
- Operation endpoint: `http://127.0.0.1:8010/mcp`
- Development endpoint: `http://127.0.0.1:8011/mcp`
- Separate profile names: `kis-mcp-operation`, `kis-mcp-development`
- External credentials: environment references only
- External instance IDs: blank with `configured: false` until supplied by the operator

## Verification commands

Baseline before implementation:

```powershell
pwsh -File .\scripts\verify.ps1
```

Result: 149 passed, 1 skipped.

Dual-instance catalogue and health smoke:

```powershell
pwsh -File .\scripts\smoke-chatgpt.ps1 -AllInstances -TimeoutSeconds 90
```

Observed for both instances:

- MCP initialization succeeded.
- Server identity was `kis-mcp`.
- Tool count was 29.
- `kis_health`, `read_file`, `write_file`, `edit_block`, and `start_process` were present.
- `give_feedback_to_desktop_commander` was absent.
- `kis_health` executed successfully.

Development write/read/quarantine smoke:

```powershell
pwsh -File .\scripts\smoke-chatgpt.ps1 -Instance development -TimeoutSeconds 90
```

Observed:

- `write_file` created a unique marker beneath `C:\Projects\.kis-mcp\temp`.
- `read_file` returned the marker.
- `kis_quarantine_path` moved the marker into recoverable quarantine.
- The source path no longer existed.
- The result reported `write_read_quarantine_ok: true`.

## Tool-exposure conclusion

The remote HTTP runtime uses the same `build_server()` instance as local stdio. It therefore exposes the same ordinary mixed-purpose provider and gateway tools and applies the same three-rule middleware. No instance profile, allowlist, approval tier, or catalogue restriction was introduced.

Only provider functionality whose every supported invocation is external-network-only remains omitted. For Desktop Commander 0.2.46 this is the feedback tool and the removed `read_file.isUrl` mode.

## External commissioning still required

For each instance, the operator must:

1. supply its real `tunnel_id` and `control_plane_scope_id` in settings;
2. set `configured` to `true`;
3. provide the configured control-plane API key environment variable;
4. create and validate the tunnel profile;
5. start the supervised launcher;
6. scan the tool catalogue from ChatGPT;
7. call `kis_health` and perform a supervised write/read/quarantine smoke from ChatGPT.

Until those steps are completed, the correct status is local HTTP commissioned and external ChatGPT tunnel pending configuration.

## Non-blocking observations

Desktop Commander emits notification-validation warnings through the FastMCP proxy because some provider log notification payloads are strings rather than the richer shape expected by the logging validator. These warnings did not prevent MCP initialization, tool discovery, health calls, or write/read/quarantine execution. They are existing provider/proxy logging compatibility noise, not a transport failure.
