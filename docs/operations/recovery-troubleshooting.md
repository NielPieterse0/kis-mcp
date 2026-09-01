# Recovery and Troubleshooting

> Operator runbook subordinate to [Operations](../OPERATIONS.md). Repository workflow and documentation routing remain in [AGENTS.md](../../AGENTS.md).

## Quarantine and restore

Quarantine records are stored beneath the configured quarantine root. Each operation has a unique ID, intact payload, and restoration metadata.

List recent recoverable records through `execute_change_action` using the canonical quarantine-list operation:

```json
{"operation":"kis_list_quarantine","arguments":{"limit":20}}
```

Choose the intended `operation_id`, confirm its recorded original path is the destination you intend to restore, and verify that path is currently absent. Then restore through the canonical operation:

```json
{"operation":"kis_restore_quarantine","arguments":{"operation_id":"<operation-id>"}}
```

Verify the returned record/original path and inspect the restored path after completion. Restoration fails rather than overwriting an existing original path; if it fails, resolve the reported path/state conflict rather than deleting the destination. Use the live operation schema/source for current bounds and returned fields.

Permanent disposal is intentionally not exposed as a normal Work tool.

## Development-runtime recovery

If `kis-dev` is unavailable and recovery through its MCP/tunnel path is impossible, run the repository-local recovery script from a healthy local shell:

```powershell
pwsh -File .\scripts\recover-kis-dev.ps1
```

This surface is intentionally independent of the selected MCP runtime and tunnel. It is hard-bound to `kis-dev`, delegates ownership checks and stale-instance reclamation to the normal `start-chatgpt.ps1` launcher, and never selects or mutates `kis-op`. Use `-Foreground` to keep the launcher attached while diagnosing startup output.

When the MCP path itself cannot be trusted, the same script provides a bounded repository read that does not start or contact either KIS runtime or any tunnel:

```powershell
pwsh -File .\scripts\recover-kis-dev.ps1 -ReadPath AGENTS.md
```

`-ReadPath` accepts only repository-relative UTF-8 files, rejects traversal and reparse-point targets, and caps a single diagnostic read at 1 MiB. It returns a JSON envelope with `state=read`, `recovery_surface=local-shell`, the normalized relative path, byte count, and content. This is the KIS-owned recovery/read contract; it remains usable even when the selected MCP route cannot answer.

Do not conflate transport failures with the no-auth metadata behavior fixed under #609. An OAuth discovery 404 from the optional protected-resource metadata probe is allowed for the configured no-auth tunnel profile. By contrast, a failed `mcp-tool.fetch` operation reported as `invalid_mcp_response` after an MCP probe returns 404, 429, or 5xx is an operation failure and must remain an error. The independent local-shell read above bypasses that connector/tunnel boundary rather than treating its failed response as successful content.

## Troubleshooting

- `KIS_DEV_RECOVERY_START_SCRIPT_MISSING`: restore the repository checkout's canonical `scripts\start-chatgpt.ps1` before attempting recovery.
- `KIS_DEV_RECOVERY_DETACH_FAILED`: detached Windows process creation failed; retry with `-Foreground` to expose the underlying launcher failure directly.
- `KIS_DEV_RECOVERY_READ_PATH_INVALID`: use a repository-relative path with no `.` or `..` traversal segment.
- `KIS_DEV_RECOVERY_READ_NOT_FOUND`: verify the requested diagnostic file exists in the authoritative checkout.
- `KIS_DEV_RECOVERY_READ_REPARSE_POINT`: do not route recovery reads through links, junctions, or other reparse points.
- `KIS_DEV_RECOVERY_READ_TOO_LARGE`: select a diagnostic UTF-8 file no larger than 1 MiB.
- `KIS_DEV_RECOVERY_READ_NOT_UTF8`: use a text diagnostic artifact; binary recovery reads are not part of this surface.
- `KIS_DEV_RECOVERY_MODE_INVALID`: do not combine `-ReadPath` with the foreground launcher mode.
- `KIS_MCP_SOURCE_CHECKOUT_REQUIRED`: run the CLI/scripts from the repository checkout and restore the canonical settings/policy files identified by the error; do not substitute generated state or a standalone wheel for repository authority.
- `KIS_MCP_REMOTE_INSTANCE_NOT_CONFIGURED`: enter the real tunnel ID for the selected instance, set `configured` to `true`, and store its credential before setup or startup.
- A missing vault entry for the selected tunnel reference: run `scripts\set-tunnel-credential.ps1` for that instance, then retry.
- `KIS_MCP_TUNNEL_SECRET_REFERENCE_MISSING` or `KIS_MCP_TUNNEL_SECRET_REFERENCE_INVALID`: restore the selected instance's canonical non-secret `tunnel_secret_ref` in JSON.
- `KIS_MCP_TUNNEL_CLIENT_MISSING`: restore the executable at the selected instance's settings-defined tunnel-client path or correct the JSON setting.
- `KIS_MCP_TUNNEL_PROFILE_EXISTS`: rerun setup with `-BackupExistingProfile` only when replacement is intended.
- `KIS_MCP_TUNNEL_PROFILE_INVALID`: inspect the tunnel-client doctor output; do not start the profile until all checks pass.
- `KIS_MCP_TUNNEL_PROFILE_MISSING`: run `scripts\setup-tunnel.ps1` for the selected instance.
- `KIS_MCP_AUTHENTICATION_TIMEOUT_INVALID`: use a timeout accepted by the current launcher contract or restore the launcher default; inspect the script/tests for current bounds.
- `KIS_MCP_PORT_OWNED_BY_OTHER_PROCESS`: the selected instance port belongs to a process that does not match the selected KIS runtime identity; inspect the reported PID/process and stop or reconfigure it explicitly. The launcher will not terminate it.
- `KIS_MCP_STALE_PORT_NOT_RELEASED`: a positively identified stale selected-instance runtime did not release its configured port after reclamation; inspect that instance's process tree before retrying.
- `KIS_MCP_ENDPOINT_OWNER_INVALID` or `KIS_MCP_ENDPOINT_OWNER_STALE`: the newly started selected runtime answered incorrectly or does not own the configured listener; startup cleans up its owned process tree rather than declaring readiness.
- `KIS_MCP_SMOKE_PORT_IN_USE`: stop the listener used by the temporary smoke endpoint or choose the intended smoke instance.
- `KIS_MCP_HTTP_NOT_READY` or `KIS_MCP_SMOKE_INITIALIZE_FAILED`: inspect Desktop Commander readiness, the Python environment, and the selected loopback endpoint.
- `KIS_MCP_TUNNEL_NOT_READY`: inspect tunnel-client output, the configured tunnel association, runtime key, and control-plane scope.
- `KIS_MCP_SMOKE_TOOLS_MISSING`: stop commissioning; the remote catalogue is reduced or the provider contract changed.
- `KIS_MCP_SMOKE_NETWORK_ONLY_TOOL_EXPOSED`: stop commissioning; the proven network-only feedback tool must not be exposed.
- `KIS_MCP_SMOKE_DISCOVER_CALL_FAILED`: inspect the `inspect_project` tool result, repository path, Discover settings, and configured budgets before retrying.
- `KIS_MCP_SMOKE_WRITE_CALL_FAILED`, `KIS_MCP_SMOKE_READ_CALL_FAILED`, or `KIS_MCP_SMOKE_QUARANTINE_CALL_FAILED`: inspect the corresponding MCP tool result and quarantine state before retrying.

- `DESKTOP_COMMANDER_ARCHIVE_NOT_FOUND`: place the configured scanned `.tgz` in the current user's `Downloads` directory.
- `DESKTOP_COMMANDER_ARCHIVE_HASH_MISMATCH`: stop; the archive differs from the recorded scanned digest.
- `DESKTOP_COMMANDER_OFFLINE_INSTALL_FAILED`: the scanned project-local npm cache does not contain the complete runtime dependency closure; run `prepare-desktop-commander-cache.ps1`, then retry without enabling registry fallback.
- `DESKTOP_COMMANDER_DEPENDENCY_ACQUISITION_FAILED`: the supervised dependency download failed; inspect the retained acquisition directory and npm log before retrying.
- `DESKTOP_COMMANDER_DEPENDENCY_SCAN_FAILED`: Defender did not return a clean result; nothing was promoted. Keep the acquisition tree isolated for operator review.
- `DESKTOP_COMMANDER_CACHE_PROMOTION_FAILED`: cache activation failed; the prior cache is restored when possible and the clean acquisition tree remains recoverable.

- `DESKTOP_COMMANDER_NOT_INSTALLED`: run the supervised install script outside Work.
- `POLICY_RULE_SET_INVALID`: restore the exact three-rule JSON file.
- `HR-001_WRITE_OUTSIDE_PROJECTS`: choose a destination beneath `C:\Projects`.
- `HR-002_EXTERNAL_NETWORK`: remove the concrete external target, use an approved connector, or use an explicit operator action outside Work.
- `UNSUPPORTED_PROVIDER_TOOL` or `UNSUPPORTED_PROVIDER_MODE`: use the exposed local provider contract; the named external-only provider surface is not part of Work.
- `PROVIDER_CONFIGURATION_INVARIANT`: leave Desktop Commander's provider-native restriction fields gateway-managed and empty.
- `INVALID_INVOCATION_PATH`: provide a concrete path that can be resolved and safely transformed.
- `HR-003_QUARANTINE_REQUIRED`: allow the gateway to move the target to quarantine rather than delete it.
- `HR-003_QUARANTINE_FAILED`: inspect quarantine availability and retry without permanent deletion.
