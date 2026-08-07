# Closeout: Startup and Control Center Commissioning

## Implemented scope

- Control Center readiness now reports the mounted local app as `Ready — local read-only` with no commissioning action required.
- Control Center rendering collapses all-`not_applicable` local commissioning stages into a concise `Local read-only` indication instead of presenting them as unresolved work.
- `RuntimeConfig` exposes validated `remote_mcp.stateless_http` and `remote_mcp.json_response` values; `remote_runtime.py` now passes those values to FastMCP instead of hard-coding stateful HTTP.
- `start.ps1` starts `python -m kis_mcp.server` directly and performs no vault unlock.
- `start-chatgpt.ps1` starts `python -m kis_mcp.remote_runtime --instance <name>` directly and performs no vault unlock.
- Selected-instance lifecycle matching was updated to the direct remote-runtime process identity while preserving bounded stale-process ownership checks.
- Tunnel credentials remain represented in checked-in settings only by canonical `secret://tunnel/<instance>/authentication-token` references.
- The canonical reference is validated and mapped to the per-user Windows Credential Manager target `kis-mcp/tunnel/<instance>`.
- `set-tunnel-credential.ps1` is the explicit one-time credential-change operation; normal setup/startup retrieves the stored credential non-interactively and exposes it only to the owned tunnel-client process environment.
- The encrypted application vault remains available for explicit vault maintenance/future vault-backed consumers but is no longer coupled to ordinary gateway startup.

## Validation evidence

- TDD regressions were demonstrated failing before implementation for local commissioning rendering and stateless-runtime configuration.
- Focused Control Center tests: passed.
- Focused remote-runtime tests: passed.
- Startup/tunnel/source-contract tests: passed.
- Secrets regression suite after startup-contract correction: passed.
- Combined focused suite covering Control Center, remote runtime, startup, tunnel, startup hardening, and Secrets: passed.
- PowerShell parser validation passed for all changed startup/tunnel scripts.
- `git diff --check`: passed.
- Change governance `validate` and `check`: passed with all changed paths inside change 077.
- Canonical `scripts/verify.ps1`: passed full pytest, Python syntax, locked interpreter/dependencies, repository line endings, configuration, change governance, and exact HR-001/HR-002/HR-003 validation.
- Isolated loopback stateless transport proof using the 077 source and configured transport flags: `initialize` = 200, no `Mcp-Session-Id`; subsequent `tools/list` = 200, no `Mcp-Session-Id`, tool discovery successful.
- Temporary proof listener on `127.0.0.1:18077` was terminated and the port released.
- Both existing per-user tunnel Credential Manager targets are present: operation and development. No credential migration prompt is required.
- Ports 8010 and 8011 were not reclaimed for smoke testing because active supervised instances are running; the observed operation listener is the pre-change secrets-launcher runtime and was deliberately left untouched for parallel-work safety.

## Review

- `inspect_change` reported high-confidence bounded change discovery with no diagnostics.
- Advisory code review returned no material defects; its observations were low-severity confirmations of intended behavior.
- Secret-path review confirms normal startup scripts contain no `Get-KisMcpUnlockPayload`, `kis_mcp.secrets.launcher`, `Start-KisMcpSecretAwareProcess`, or `Unlock kis-mcp secrets` references.

## Git and merge

- Branch: `change/077-control-center-commissioning-status`
- Worktree: `.work/worktrees/077-control-center-commissioning-status`
- Commit: branch contains the verified implementation commit plus a non-rewriting merge of current `origin/main`; final exact SHA is recorded in PR metadata after the closeout update commit.
- Pull request: #88 — `https://github.com/NielPieterse0/kis-mcp/pull/88`.
- Landing: pending required exact-head PR completion gate; no merge mutation has been requested.
- Cleanup: pending merge; use `change-workflow.ps1 cleanup 077-control-center-commissioning-status` only from clean `main` after merge.

## Residual / integration items

- Active change `078-project-registry-routing` currently owns `SPEC.md`, `docs/OPERATIONS.md`, and `docs/PLATFORM-CONCEPT.md`; change 077 intentionally did not cross that ownership boundary.
- `docs/STARTUP-HARDENING.md` and `docs/development/secrets/README.md` are reconciled in this change. The three authority documents above must adopt the same promptless-startup/vault-separation wording after change 078 releases or integrates those paths.
- The currently running kis-op/kis-dev processes were started from pre-change code. The corrected startup/UI behavior becomes live on their next normal supervised restart after this change is merged; no active parallel instance was terminated to prove that transition.
