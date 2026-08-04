# Startup Hardening Closeout

Status: implementation verified

Remote publication is reported separately after the commit is pushed and the pull request exists; this committed closeout does not claim future GitHub state.

## Implemented

- Built the complete Startup Hardening delta as one commit from exact base `0915bfa67e4452240d2c5fef677670c0c68386c7`, then merged current `origin/main` after PRs #14 and #15 advanced the integration base.
- Transferred further startup correction ownership from closed change `007` to change `013` without editing the preserved `007` worktree.
- Absorbed the committed non-secret tunnel identifier schema required by commissioning.
- Replaced file-based tunnel secret handling with per-user Windows Credential Manager storage, non-secret JSON target names, and transient owned-process injection.
- Added `provider_startup_compat.cjs` and lifecycle preload wiring.
- Contained the exact Desktop Commander feature-flag request locally.
- Suppressed provider log notifications and stripped provider UI metadata.
- Removed five provider administration tools before FastMCP constructs the public catalogue.
- Kept startup compatibility behavior out of Work middleware and the Desktop Commander effect resolver.
- Disabled the FastMCP startup banner.
- Separated static profile generation from optional live endpoint validation.
- Classified endpoint unavailability as `KIS_MCP_ENDPOINT_NOT_READY` rather than invalid profile state.
- Sequenced local MCP readiness before tunnel startup.
- Added bounded observation mode and normal owned-process cleanup.
- Captured setup, server, and tunnel diagnostics beneath the instance runtime root.
- Reduced the operator console to bounded kis-mcp profile and readiness fields.
- Recorded read-set, edit-set, and six change-reason clusters as MAS measurement 1 of 2.

## Verification

Fresh integrated verification on August 4, 2026 after merging current `origin/main`:

```powershell
pwsh -NoProfile -File scripts/verify.ps1
```

Result: exit code `0`.

Verified:

- exact three-rule configuration;
- locked interpreter and dependencies;
- Python syntax;
- governance across twelve coordinated claims;
- complete pytest suite with two expected skips.

Live bounded observation:

- isolated endpoint: `127.0.0.1:8012`;
- observation duration: eight seconds;
- local MCP readiness: passed;
- tunnel readiness: passed;
- owned-process cleanup: passed;
- settings restoration: byte-for-byte passed;
- operator console cleanliness: passed;
- occupied port `8011` runtime: untouched.

Forbidden console patterns were all absent, including malformed provider notifications, feature-flag startup messages, FastMCP promotion, tunnel Fx/admin/startup output, and Uvicorn transport output.

## Review

The change remains within the declared Startup Hardening paths. The following files match the exact base and are absent from the diff:

- `src/kis_mcp/middleware.py`
- `src/kis_mcp/desktop_commander.py`
- `tests/test_middleware.py`
- Skills, Discover implementation, and provider implementation paths

No credential values, generated profiles, runtime logs, caches, or observation artifacts are committed.

An independent subagent reviewer was not available in this chat runtime. Final review therefore consists of fresh automated verification, live observation, scope checking, secret inspection, and a manual complete-diff review.

## Recovery

Revert the Startup Hardening feature commit or the merged pull request. Generated profile YAML is never permanently deleted: replacement requires `-BackupExistingProfile`, which moves the previous profile beneath the profile backup directory. The Windows Credential Manager entry remains operator-owned and is not copied, logged, or deleted by rollback.

## Residual risks

- Owned child stdout and stderr are drained asynchronously but materialized into their diagnostic files during launcher cleanup; unusually long sessions may retain accumulated output in memory until shutdown. Streaming file capture is deferred.
- Tunnel-client remains externally networked by design and continues to produce verbose internal diagnostics in its local runtime log; these no longer reach the operator console.
- The temporary observation used port `8012` because port `8011` was occupied by another kis-mcp development runtime. The production instance-specific ports remain governed by settings and collision checks.
- A real MAS score is intentionally deferred until a second substantial slice records the same read-set, edit-set, and change-reason measurements.
