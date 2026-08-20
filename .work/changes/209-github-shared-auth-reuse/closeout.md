# Closeout: GitHub Shared Auth Reuse

## Implemented scope

- Added provider-local GitHub CLI shared-auth resolution for `github.com`.
- Valid CLI-managed auth is reused only in process memory and passed only to the GitHub MCP child.
- Missing/invalid CLI auth preserves token-free interactive OAuth fallback.
- Ambient PAT remains a configuration conflict and is never silently reused.
- Startup/health observability reports only redacted source/state/reason fields.
- Updated operator guidance and current-product specification for reuse-first restart behavior.

## Validation evidence

- Focused suite: `pwsh -NoProfile -File scripts/smoke-github-mcp.ps1` — passed (148 tests; non-live smoke).
- Targeted auth/server tests: locked interpreter `python -m pytest tests/providers/github/test_auth.py tests/providers/github/test_server.py -q` — 11 passed before full focused suite expansion.
- Ruff: affected GitHub provider/test paths — passed.
- Scope: `pwsh -NoProfile -File scripts/change-workflow.ps1 check` — passed; all changed paths owned by Change 209.
- Live credential preflight: configured `gh` profile reported active `github.com` auth and token availability without emitting credential content.
- Resolver live check: `github_cli_keyring / shared_auth_reused / github_cli_active_auth_valid`; token value not emitted.

## Review

- Required `code-quality`: full-diff implementation review completed after the last behavior/test change; no findings.
- Required `safety-security`: full-diff implementation review completed after the last behavior/test change; no findings.
- Earlier review test-coverage finding was resolved by asserting redacted health fields and exercising shared-auth server construction/log redaction.
- Earlier empty-`PATH` recommendation was not adopted: the minimal environment contract intentionally excludes empty values; forwarding an explicitly empty `PATH` would not make `gh` discoverable.

## Git and merge

- Branch: `change/209-github-shared-auth-reuse`
- Worktree: `.work/worktrees/209-github-shared-auth-reuse`
- Base: `00996bebba601c819018f438b19aad58e18520ee`
- Final commit / PR / Actions / merge: completed through external exact-head evidence after this immutable repository record is committed.
- Cleanup: governed cleanup after verified merge and refreshed `main`.

## Residual items

- None inside Change 209. #397, Work Management reconciliation, and #391 remain excluded.
