# Change Specification: Operational Status Closeout

- **Change ID**: `086-operational-status-closeout`
- **Status**: Approved for implementation by operator request
- **Development level**: Small
- **Risk Profile**: standard

## Outcome

Make Supabase registered-project live verification and remote MCP commissioning status reflect current runtime evidence instead of stale hard-coded labels.

## Authority and scope

- Authorities: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, `policy/kis-mcp.policy.json`, `docs/OPERATIONS.md`.
- Scope is limited to the owned paths in `scope.json`.
- Active changes 040, 084, and 085 remain untouched.
- No policy, provider routing authorization, secrets, external network bootstrap, or `origin/main` push changes are included.

## Requirements

- **REQ-001**: A successful Supabase read carrying a registered `project_id` and an upstream read-only annotation records process-local live-verification evidence.
- **REQ-002**: `kis_provider_status` reports `live_verified=ready_registered_project_read` only after REQ-001 evidence exists in the current provider runtime; otherwise it remains pending or blocked as appropriate.
- **REQ-003**: A remote HTTP runtime identifies its selected instance process-locally without changing checked-in settings.
- **REQ-004**: `kis_health.implementation_status.remote_mcp` upgrades the stale static label to `external_tunnel_ready` only when the selected instance `current.json` proves `lifecycle=ready`, endpoint/instance identity match, and the recorded listener PID is the current serving process.

## Acceptance

1. Given an authenticated Supabase runtime with no successful registered-project read, provider status remains pending live verification.
2. Given a successful registered-project read, provider status reports live verification ready in the same runtime.
3. Failed calls, writes, targetless account reads, and unregistered project calls do not mark registered-project live verification.
4. Given a matching ready `current.json` for the running remote instance, `kis_health` reports `external_tunnel_ready` instead of the stale pending-configuration value.
5. Missing, malformed, stopped, wrong-instance, wrong-endpoint, or wrong-listener state never upgrades the static status.
6. Focused tests, change-scope validation, and canonical `scripts/verify.ps1` pass on the final branch.

## Risks and recovery

- Risk: false-positive commissioning status from stale generated state. Mitigation: bind evidence to selected instance, canonical endpoint, lifecycle, and current listener PID.
- Risk: successful mutations accidentally counted as commissioning reads. Mitigation: require upstream `readOnlyHint` plus registered `project_id` and successful completion.
- Recovery: revert the bounded branch; process-local commissioning evidence resets on runtime restart and no persistent migration is introduced.

## Out of scope

- Editing `settings/kis-mcp.settings.json` while change 084 owns it.
- Changing policy, authorization, provider credentials, tunnel configuration, or active worktrees 040/084/085.
- Pushing local `main` to `origin/main`.
