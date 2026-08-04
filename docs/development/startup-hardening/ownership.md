# Startup Hardening Ownership

## Decision

Change `007-chatgpt-remote-commissioning` is closed on `main`. Change `013-startup-hardening` is the sole owner of further startup-hardening corrections within its declared paths.

This decision does not reopen or mutate the `007` worktree. The existing `007` checkout may remain present for another agent or for preservation of uncommitted operator experiments, but it is not an implementation source for `013`.

## Ownership boundary

Change `013` owns:

- `settings/kis-mcp.settings.json` for the non-secret tunnel identifier schema only
- `src/kis_mcp/config.py`
- `src/kis_mcp/provider_startup_compat.cjs`
- `src/kis_mcp/provider_lifecycle.py`
- `src/kis_mcp/remote_runtime.py`
- `scripts/tunnel-state.ps1`
- `scripts/setup-tunnel.ps1`
- `scripts/start-chatgpt.ps1`
- the directly corresponding tests and startup-hardening documentation declared in `scope.json`

Change `013` does not own and must not edit:

- `src/kis_mcp/middleware.py`
- `src/kis_mcp/desktop_commander.py`
- Skills, Discover, provider-module, GitHub, or Supabase implementation paths
- credential values, generated profiles, or operator-managed runtime state

## Compatibility seam

All Desktop Commander startup compatibility behavior is concentrated in:

```text
provider_lifecycle.py
        |
        +-- provider_state_atomic.cjs
        |
        +-- provider_startup_compat.cjs
```

The startup compatibility adapter may:

- satisfy the exact configured feature-flag request locally;
- suppress provider log notifications;
- strip provider-specific UI metadata from `tools/list` while preserving provider tool names and schemas.

The adapter must not alter ordinary tool availability, requests, results, errors, non-log notifications, or Work policy evaluation.

## Base and integration

The final `013` branch history must be linear from exact base:

```text
0915bfa67e4452240d2c5fef677670c0c68386c7
```

No Startup Hardening commit may be based on, merged from, or force-integrated with another active agent worktree after this ownership decision.
