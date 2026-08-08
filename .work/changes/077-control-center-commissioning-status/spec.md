# Change Specification: Startup and Control Center Closeout

- **Change ID**: `077-control-center-commissioning-status`
- **Status**: Approved by operator request of 2026-08-08
- **Risk Profile**: rigorous
- **Development level**: Medium — startup transport, local credential handling, UI status, and lifecycle matching change together.

## Outcome

Close three commissioning defects without changing the three-rule policy: report truthful local Control Center status, make the remote MCP runtime actually stateless as configured, and remove interactive vault unlock from normal server/tunnel startup.

## Authority and scope

- Authority: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, `policy/kis-mcp.policy.json`, then `docs/OPERATIONS.md`, plus the operator's explicit 2026-08-08 correction.
- Owned and excluded paths are defined by `scope.json`.
- `SPEC.md`, `docs/OPERATIONS.md`, and `docs/PLATFORM-CONCEPT.md` are excluded because active change `078-project-registry-routing` owns them.
- No network access is added to Work and no permanent-delete behavior changes.

## Requirements

- **REQ-001 — Local UI truth**: Control Center readiness must identify the mounted Control Center as local read-only and requiring no commissioning action.
- **REQ-002 — UI signal quality**: The UI must not present `not_applicable` commissioning stages as unresolved work; local-only providers should render a concise neutral/ready indication.
- **REQ-003 — Stateless HTTP**: `run_remote_instance` must use the checked-in `remote_mcp.stateless_http` and `json_response` settings. The canonical settings require both to be `true`.
- **REQ-004 — Smoke compatibility**: A successful `initialize` request must not create a mandatory session dependency for subsequent `tools/list` or `tools/call` requests.
- **REQ-005 — Promptless server startup**: `start.ps1` and the server child in `start-chatgpt.ps1` must launch the normal runtime directly and must not unlock or initialize the application vault.
- **REQ-006 — Promptless tunnel startup**: tunnel authentication must be retrieved non-interactively from the current Windows user's Generic Credential entry and injected only into the owned tunnel-client environment.
- **REQ-007 — One-time credential change**: `set-tunnel-credential.ps1` remains the operator action that prompts for a new tunnel credential; startup never prompts for either the tunnel key or vault unlock material.
- **REQ-008 — Canonical references**: checked-in settings continue to hold only canonical `secret://tunnel/<instance>/authentication-token` references. The Windows credential target is derived deterministically as `kis-mcp/tunnel/<instance>`.
- **REQ-009 — No plaintext persistence**: tunnel credentials must not be written to repository JSON, tunnel profile YAML, logs, runtime-state JSON, or command-line arguments.
- **REQ-010 — Lifecycle ownership**: stale-process detection and endpoint ownership checks must recognize the direct `python -m kis_mcp.remote_runtime --instance <name>` server command.
- **REQ-011 — Vault separation**: the encrypted application vault remains available for explicit vault maintenance workflows, but ordinary gateway startup does not keep it unlocked.
- **REQ-012 — Documentation**: update unclaimed startup/secrets documentation now; record the active-claim authority-document reconciliation as an explicit integration item rather than editing change 078's paths.

## Acceptance

1. Given the Control Center provider is mounted, provider status and rendered UI state show local read-only readiness with no commissioning action.
2. Given canonical settings specify stateless HTTP, the remote runtime passes `stateless_http=True` and `json_response=True` to FastMCP and the smoke sequence does not require a session header.
3. Given a stored per-user tunnel credential, starting `kis-op` or `kis-dev` does not display `Unlock kis-mcp secrets` and starts the server before the tunnel as today.
4. Given the credential is missing, startup fails with a bounded `KIS_MCP_TUNNEL_CREDENTIAL_MISSING` error and does not move or overwrite the credential/profile automatically.
5. Given startup preflight sees a prior selected runtime, it recognizes and safely reclaims only the selected direct remote-runtime process tree.
6. Given the final worktree head, focused tests, change governance, architecture checks, and `scripts/verify.ps1` pass.

## Risks and recovery

- **Credential backend regression**: Windows Credential Manager is user-scoped; missing entries fail closed and can be recreated with `set-tunnel-credential.ps1`.
- **Parallel documentation claim**: authority docs remain untouched while 078 owns them; reconcile only after that claim is released.
- **Recovery**: revert this change; prior encrypted vault artifacts are preserved and no permanent deletion is introduced.

## Out of scope

- Changing the three hard policy rules.
- Changing Supabase or provider-specific credential storage.
- Editing paths currently owned by change 078.
- Removing the generic encrypted vault implementation or its explicit maintenance commands.
