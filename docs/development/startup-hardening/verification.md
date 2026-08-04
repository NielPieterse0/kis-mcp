# Startup Hardening Verification

## Baseline

- Exact base: `0915bfa67e4452240d2c5fef677670c0c68386c7`
- Branch: `change/013-startup-hardening`
- Isolation: only the `013-startup-hardening` worktree was modified.
- Parallel worktrees: preserved without edits or process termination.

## Automated verification

The locked repository verification completed successfully on August 4, 2026:

```powershell
pwsh -NoProfile -File scripts/verify.ps1
```

Verified outcomes:

- settings and policy parse;
- policy contains exactly HR-001, HR-002, and HR-003;
- locked Python environment and dependency versions match configuration;
- Python syntax passes;
- change governance passes with ten claims;
- the complete pytest suite passes with two expected skips.

The focused startup checks also pass:

```powershell
python -m pytest `
  tests/test_provider_lifecycle.py `
  tests/test_startup_hardening.py `
  tests/test_startup_scripts.py `
  tests/test_tunnel_scripts.py `
  tests/test_remote_runtime.py `
  -q
```

## Live bounded observation

A supervised observation used an isolated temporary development endpoint on `127.0.0.1:8012`. The already occupied development endpoint on port `8011` was not stopped or modified.

Observed sequence:

1. generated and backed up the temporary observation profile;
2. started the local kis-mcp HTTP runtime;
3. completed MCP initialization readiness;
4. started the tunnel client;
5. reached tunnel readiness;
6. remained healthy for eight seconds;
7. stopped both owned processes through normal launcher cleanup;
8. restored `settings/kis-mcp.settings.json` byte-for-byte.

Evidence summary:

```json
{
  "succeeded": true,
  "settings_restored": true,
  "console_clean": true,
  "observation_port": 8012,
  "observation_profile": "kis-mcp-development-observation"
}
```

The console contained only kis-mcp profile and readiness fields. The following patterns were absent:

- malformed FastMCP notification warnings;
- Desktop Commander feature-flag failures or initialization messages;
- Desktop Commander onboarding output;
- FastMCP update or deployment promotion;
- tunnel-client Fx wiring, admin UI, and startup summary output;
- Uvicorn transport output.

Child diagnostics remained available in the four log paths recorded by the generated startup-state JSON. The tunnel log contained the expected detailed tunnel-client diagnostics, proving output was retained rather than discarded.

## Review boundary

Startup compatibility is localized to:

```text
provider_lifecycle.py
├── provider_state_atomic.cjs
└── provider_startup_compat.cjs
```

`src/kis_mcp/middleware.py`, `src/kis_mcp/desktop_commander.py`, and `tests/test_middleware.py` match the exact base and are absent from the change diff.

No credential values, generated profiles, runtime logs, or temporary observation files are committed.
