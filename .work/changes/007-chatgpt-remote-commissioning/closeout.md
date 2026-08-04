# Closeout: ChatGPT Remote Commissioning

- **Status**: Ready for review; external tunnel configuration pending operator IDs
- **Development level**: Complex — remote transport, external tunnel process lifecycle, dual-instance switching, and operational recovery

## Implemented scope

- Added canonical `remote_mcp` JSON settings for `operation` and `development`.
- Added strict loopback, endpoint, profile, port, tunnel-identifier validation.
- Added `kis_mcp.remote_runtime`, reusing the same `build_server()` gateway and three-rule middleware as stdio.
- Added settings-backed tunnel state, profile setup, doctor validation, supervised launch, readiness, paired shutdown, and exclusive instance switch-over.
- Added a local behavioral smoke test covering MCP initialization, tool discovery, `kis_health`, real write/read execution, and recoverable quarantine.
- Preserved the full mixed-purpose tool surface. Only the necessarily network-only feedback tool and `read_file.isUrl` remain absent.
- Updated the product specification, operations runbook, and commissioning evidence.

## Review

No blocking correctness, policy, secret-handling, lifecycle, or scope findings remained after review.

One operational issue was found and fixed: the launcher originally allowed both ChatGPT-facing instances to run simultaneously against shared provider state. It now refuses startup while the other instance is listening.

One blocking tunnel-authentication issue was found and fixed during PR review: removing the explicit API-key reference caused `tunnel-client init` to silently restore its default `env:CONTROL_PLANE_API_KEY` dependency. Setup now materializes the stored tunnel authentication ID to generated state and passes the tunnel client's validated `file:` reference, with no environment-variable dependency.

One diff-quality issue was found and fixed: edits had converted three existing files to CRLF. They were restored to their original LF format before commit.

## Verification

Baseline before implementation:

```powershell
pwsh -File .\scripts\verify.ps1
```

Result: 149 passed, 1 skipped.

Final authoritative verification:

```powershell
pwsh -File .\scripts\verify.ps1
```

Result: 158 passed, 1 skipped; configuration, interpreter, dependencies, syntax, governance verifier, pytest, and exact three-rule checks passed.

Final governed scope check:

```powershell
pwsh -File .\scripts\change-workflow.ps1 check
```

Result: passed; all 17 changed paths were declared owned or shared paths.

Final local dual-instance behavioral smoke:

```powershell
pwsh -File .\scripts\smoke-chatgpt.ps1 -AllInstances -TimeoutSeconds 90
```

Result for both `operation` and `development`:

- endpoint initialized successfully;
- server identity `kis-mcp`;
- 29 tools exposed;
- `kis_health`, `read_file`, `write_file`, `edit_block`, and `start_process` present;
- necessarily network-only feedback tool absent;
- `kis_health` succeeded;
- write/read/quarantine succeeded.

Whitespace validation:

```text
git diff --check
```

Result: passed after removing one trailing blank line.

## Recovery

- Stop `scripts\start-chatgpt.ps1`; its `finally` block stops both owned processes.
- Existing tunnel profiles are never overwritten without `-BackupExistingProfile`; replacements preserve the old profile and generated authentication file beneath the project-local backup directory.
- The smoke test quarantines generated markers and attempts best-effort quarantine on failure.
- Local `scripts\start.ps1` stdio behavior remains unchanged.
- Before merge, the isolated branch/worktree can be removed through normal Git worktree cleanup.

## Residual risks and deferred evidence

- The four permanent identifier values were not available in repository-readable state during this correction, so the settings fields remain blank pending one-time entry and commit.
- A live tunnel-client run, ChatGPT custom-app tool scan, and ChatGPT-originated write/read/quarantine smoke were not performed and are not claimed.
- Desktop Commander emits pre-existing FastMCP notification-validation warnings for some string logging payloads. They did not affect initialization, discovery, health, or file/quarantine execution.
