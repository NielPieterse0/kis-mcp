# Closeout: Independent Recovery Read

## Implemented scope

- Reproduced the legacy independent `mcp-tool.fetch` failure as `invalid_mcp_response`; current live probe returns HTTP 429 at the platform tunnel before file handling.
- Added `recover-kis-dev.ps1 -ReadPath` as a KIS-owned local-shell diagnostic read independent of KIS runtimes and tunnels.
- Added traversal, component reparse-point, existence, 1 MiB, and strict UTF-8 guards while preserving existing `kis-dev` launch behavior.
- Documented that optional no-auth OAuth discovery 404 is distinct from failed MCP operation probes on 404/429/5xx.

## Validation evidence

- Focused tests: `tests/test_startup_scripts.py` — 41 passed with canonical managed Python.
- Live read: `recover-kis-dev.ps1 -ReadPath AGENTS.md` returned `state=read`, `recovery_surface=local-shell` without runtime/tunnel dependency.
- Governed scope check: `scripts/change-workflow.ps1 check` passed with only declared paths.
- Work classification: authoritative re-read shows Change `620-independent-recovery-read`, complexity `medium`, stage `change_created`.

## Review

- Code-quality specialist review: clean, no findings.
- Independent kis-op safety/security review: clean, no findings; no kis-op mutation performed.
- Primary security projector was incomplete because it omitted the PowerShell source; it was not counted as clean evidence.

## Git and merge

- Branch: `change/620-independent-recovery-read`
- Worktree: `.work/worktrees/620-independent-recovery-read`
- Publication, exact-head Actions, merge, Work completion, and cleanup are performed by the governed landing workflow after this implementation evidence is committed.

## Residual items

- The separate legacy `mcp-tool` connector/tunnel remains an external failing route; this change does not mutate or mask that platform-managed failure.