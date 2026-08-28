# Change: Tunnel Client Project Path

- **Change ID**: `257-tunnel-client-project-path`
- **Risk Profile**: lean

## Outcome

Move the configured OpenAI tunnel client executable path under C:\Projects and reconcile current architecture documentation.

## Scope and acceptance

- Move `settings.remote_mcp.tunnel_client_path` to `C:\Projects\.tools\openai-tunnel-client\tunnel-client.exe`.
- Keep current architecture documentation and path assertions aligned with that canonical setting.
- Keep canonical CI tool execution under `C:\Projects` by staging `uv` under `C:\Projects\.tools\uv\bin` and directing uv-managed Python/tools there.
- Preserve all tunnel IDs, profiles, credentials, instance ports, and runtime semantics unchanged.

## Implementation and verification

- Implementation notes: updated the canonical tunnel setting, `SPEC.md`, the two path assertions, and canonical GitHub verification so its effective `uv`/uv-managed tool paths are under `C:\Projects\.tools\uv`.
- Focused checks: settings JSON parsed successfully; `load_runtime_config()` resolved the new path; `scripts/change-workflow.ps1 check` passed. Direct pytest launch was blocked by Windows Application Control and the current locked Python environment does not contain pytest, so exact-head GitHub verification remains the authoritative full test gate.
- Review findings: bounded diff contains only the intended path relocation and matching documentation/test expectations.
- Residual risk: the executable itself is generated/operator-managed state outside repository authority; repository verification can prove configuration consistency but not future file presence.
- Closeout state: implementation complete; publication and exact-head GitHub verification pending.
