# Change Specification: Dual Instance Commissioning

- **Change ID**: `041-dual-instance-commissioning`
- **Status**: Approved
- **Development level**: Complex
- **Risk profile**: rigorous operational change

## Outcome

Allow the two commissioned ChatGPT tools, `kis-op` and `kis-dev`, to run concurrently through one lean selector-based launcher while proving that each app is bound only to its canonical local port and tunnel identity.

## Authority and scope

- Authoritative sources: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `settings/kis-mcp.settings.json`, `docs/OPERATIONS.md`, and the operator approvals in this change.
- Canonical internal instances remain `operation` and `development`.
- Canonical external ChatGPT app names are `kis-op` and `kis-dev`.
- Canonical ports are `operation`/`kis-op` on `127.0.0.1:8010` and `development`/`kis-dev` on `127.0.0.1:8011`.
- Owned paths are recorded in `scope.json`.
- This change does not modify HR-001, HR-002, HR-003, provider tool exposure, tunnel IDs, or secret values.

## Requirements

- **REQ-001 — Concurrent operation:** Starting `kis-dev` must not stop, reject, reconfigure, or otherwise disturb a listening `kis-op` instance, and vice versa.
- **REQ-002 — Canonical identity:** JSON configuration must record the external app identity for each canonical internal instance: `operation` maps to `kis-op`; `development` maps to `kis-dev`.
- **REQ-003 — Port hardening:** Runtime configuration validation must reject any mapping other than `kis-op`/`operation`/`8010` and `kis-dev`/`development`/`8011`, reject duplicate instance ports, and retain loopback-only endpoints.
- **REQ-004 — Own-port exclusivity:** The launcher must reject startup only when the selected instance's own configured port is already listening. A listener on the peer instance's canonical port is permitted.
- **REQ-005 — Lean selection:** One launcher remains authoritative. It accepts `kis-op` and `kis-dev` as the preferred selectors, retains `operation` and `development` for compatibility, and may accept the short aliases `op` and `dev`. Omitting the selector continues to use `settings.remote_mcp.active_instance`.
- **REQ-006 — Observable binding:** Successful startup output and the startup-state JSON must identify the external app name, canonical internal instance, exact loopback endpoint, selected tunnel profile, and selected tunnel ID.
- **REQ-007 — No automatic failover:** A failed or occupied selected instance must fail clearly; the launcher must never silently start the peer instance.
- **REQ-008 — Test-first evidence:** Regression tests must fail against the current mutual-exclusion implementation, then pass after the smallest complete change. Canonical repository verification and live dual-instance commissioning are required before closeout.

## Acceptance

1. **Given** `kis-op` is already listening on `127.0.0.1:8010`, **when** the operator starts `kis-dev`, **then** the development server binds `127.0.0.1:8011`, its own tunnel starts, and `kis-op` remains available.
2. **Given** `kis-dev` is already listening on `127.0.0.1:8011`, **when** the operator starts `kis-op`, **then** the operation server binds `127.0.0.1:8010` without disturbing `kis-dev`.
3. **Given** the selected instance's own port is occupied, **when** startup is requested, **then** startup fails before vault unlock with `KIS_MCP_PORT_IN_USE` and identifies the selected app and endpoint.
4. **Given** app names or ports are swapped, duplicated, or changed in JSON, **when** configuration is loaded, **then** startup fails with a structural instance-identity or port-mapping error.
5. **Given** any supported selector (`kis-op`, `op`, `operation`, `kis-dev`, `dev`, `development`), **when** the launcher resolves it, **then** it selects the correct canonical instance and never the peer.
6. **Given** startup succeeds, **when** readiness evidence is emitted, **then** the output and startup-state artifact agree on app, instance, endpoint, profile, tunnel ID, and policy fingerprint.
7. **Given** the current branch, **when** `scripts/change-workflow.ps1 check` and `scripts/verify.ps1` run, **then** both pass with no scope or regression failures.

## Risks and recovery

- **Risk:** Incorrect normalization could select the wrong tunnel or port. **Control:** exact app/instance/port triplet validation plus alias-resolution tests.
- **Risk:** Concurrent processes could share mutable runtime artifacts. **Control:** preserve the existing per-instance runtime directories, profile names, tunnel IDs, and log paths; test their distinctness.
- **Risk:** A commissioning run could interrupt the operational tool. **Control:** remove peer-process ownership and peer-port rejection only; never kill or modify the peer process.
- **Recovery:** Stop only the newly started development launcher, restore the prior launcher script and documentation from Git, and rerun verification. The existing operational process remains independently owned and is not part of rollback.

## Out of scope

- Changing the three-rule policy.
- Changing tunnel IDs, tunnel credentials, provider catalogue, or exposed tools.
- Automatic failover or automatic app switching.
- A new service manager, background daemon, tray application, or duplicate launcher.
- Restarting or upgrading the currently running `kis-op` instance.
