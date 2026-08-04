# GitHub OAuth Commissioning Implementation Plan

## Development level

Complex. The change crosses executable provenance, interactive OAuth, process environment handling, external connector scope, live commissioning, and shared-runtime integration. It must preserve the closed Work policy and avoid secrets.

## Task 1 — Lock the configuration contract

Files:
- `settings/providers/github-mcp.provider.json`
- `contracts/providers/github/provider-settings.schema.json`
- `src/kis_mcp/providers/github/settings.py`
- `tests/providers/github/test_settings.py`
- `tests/providers/github/test_schema.py`

Steps:
1. Write failing tests for schema version 2, pinned release tag/commit, OAuth mode, PAT-conflict environment name, and removal of PAT credential configuration.
2. Update the strict JSON schema and loader.
3. Run settings and schema tests.

## Task 2 — Make runtime readiness OAuth-correct

Files:
- `src/kis_mcp/providers/github/server.py`
- `tests/providers/github/test_server.py`
- `tests/providers/github/test_registry.py`

Steps:
1. Write failing tests proving PAT is never forwarded, PAT presence is surfaced as a conflict, executable-only local readiness is distinct from authenticated state, and the stdio launch remains token-free.
2. Update health/readiness/environment construction.
3. Preserve repository-scope middleware and descriptor composition.
4. Run server and registry tests.

## Task 3 — Implement official release installation

Files:
- `scripts/install-github-mcp.ps1`
- `tests/providers/github/test_scripts.py`

Steps:
1. Replace the historical no-download expectations with failing tests for immutable GitHub release API use, exact release tag and commit validation, Windows x86-64 asset selection, published SHA-256 verification, bounded extraction, and recoverable replacement.
2. Implement the installer without tokens or repository writes outside `C:\Projects`.
3. Add a metadata-only/preflight mode suitable for offline structural tests; do not execute network during pytest.
4. Run script tests.

## Task 4 — Add interactive OAuth commissioning

Files:
- `src/kis_mcp/providers/github/commission.py`
- `scripts/auth-github-mcp.ps1`
- `tests/providers/github/test_live_smoke.py`
- `tests/providers/github/test_scripts.py`

Steps:
1. Write failing tests for the commissioning sequence using fake clients: tool discovery, `get_me`, approved `README.md` read, and local rejection of an unapproved repository.
2. Implement a reusable async commissioning routine and JSON report.
3. Add the operator-supervised PowerShell launcher, including PAT-conflict checks and locked environment setup.
4. Run commissioning and script tests.

## Task 5 — Prove shared-runtime exposure

Files:
- `src/kis_mcp/providers/github/smoke.py`
- `scripts/smoke-github-mcp.ps1`
- `tests/providers/github/test_live_smoke.py`
- `tests/providers/github/test_scripts.py`

Steps:
1. Write failing tests that the live smoke targets `github_get_me` and `github_get_file_contents` through a shared server client and verifies `kis_provider_status` reports the GitHub mount.
2. Implement standalone and shared-runtime commissioning paths without editing `server.py`.
3. Keep offline smoke focused and explicit; require `-RequireLive` for browser/network activity.
4. Run all GitHub provider tests.

## Task 6 — Documentation, review, and verification

Files:
- `docs/development/github-mcp-provider/README.md`
- `docs/development/github-mcp-provider/verification.md`
- `.work/changes/018-github-oauth-commissioning/tasks.md`
- `.work/changes/018-github-oauth-commissioning/closeout.md`

Steps:
1. Update provider-specific operations documentation with install, OAuth, restart behavior, PAT conflict, smoke, recovery, and residual limitations.
2. Review the full diff against the specification, including secrets, policy boundary, installer provenance, scope middleware, error handling, and unnecessary complexity.
3. Run focused tests, full verification, JSON validation, syntax validation, `git diff --check`, and manual scope inspection. Run live OAuth only if the operator environment can complete it in the current session.
4. Record exact evidence and any unavailable live step without claiming it passed.
