# Closeout: Startup Runtime Reclaim

## Implemented scope

- Extended selected-server identity so Windows may resolve `ExecutablePath` to the base interpreter while the canonical project Python launcher is proven by the first command-line token.
- Preserved the exact `kis_mcp.remote_runtime --instance <selected>` requirement.
- Reused the existing `Stop-Process -Force` process-tree cleanup and `Wait-KisMcpSelectedPortReleased` gate; no arbitrary port-owner termination was added.
- Updated `docs/OPERATIONS.md` to describe the ownership rule accurately.

## Validation evidence

- TDD RED: the new canonical-launcher/base-interpreter regression test failed with `False != True` before implementation.
- Focused startup suite: `python -m pytest tests/test_startup_scripts.py -q` -> 27 passed.
- Change scope check: `pwsh -NoProfile -File scripts/change-workflow.ps1 check` accepted only declared paths.
- Repository verification: an initial full `scripts/verify.ps1` run reported `pytest exit_code=0`, `verification ok=true`, and `Verification passed`; final verification is rerun after closeout metadata is current.

## Review

- Automated advisory review was attempted first as required: NVIDIA NIM returned `AGENT_BACKEND_FAILED:NvidiaNimError`; explicit Codex CLI returned `AGENT_BACKEND_UNAVAILABLE`.
- Fallback direct review found no blocking issue: the broadened path match is anchored to the first command-line token, remains case-insensitive/path-specific, and still requires the exact selected remote-runtime instance.
- Existing unrelated-listener refusal, peer-instance isolation, forceful owned-tree stop, and selected-port release wait remain unchanged.

## Git and merge

- Branch: `change/082-startup-runtime-reclaim`
- Worktree: `.work/worktrees/082-startup-runtime-reclaim`
- Commit: pending final verification.
- Pull request or merge: pending final verification.
- Cleanup: pending merge.

## Recovery

- Revert the bounded startup identity change. The conservative prior behavior refuses an ambiguous selected-port owner rather than terminating it.

## Residual items

- None within the approved scope. Provider authentication and live `kis-op` commissioning are performed after the merged `main` restart.
