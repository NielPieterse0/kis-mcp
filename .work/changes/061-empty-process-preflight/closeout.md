# Change 061 closeout

## Status

Active. Tasks 1–4 are implemented on `change/061-empty-process-preflight`; executable verification and merge closeout remain pending.

## Implemented scope

- Empty process collections are valid startup preflight input and the startup PowerShell test helper now makes binder/runtime errors terminating.
- The persistent provider lifecycle owns startup state and a runtime tool snapshot; pre-lifespan upstream discovery is suppressed for that persistent provider, while `get_me` and initial discovery run inside the one shared client connection.
- GitHub readiness transitions to current-runtime authenticated state after startup succeeds, without claiming persistent authentication or full live verification.
- Provider runtime tool snapshots are namespaced and fed into a capability catalogue/readiness view that refreshes at use time; the direct exposure profile remains fixed and bounded.
- Existing aggregate discovery for non-GitHub mounted providers is preserved.
- The launcher separates the supervised server/OAuth timeout from the fresh tunnel readiness timeout and drains retained server stderr live for OAuth/device-code guidance.
- `docs/OPERATIONS.md` is reconciled with the implemented lifecycle.

## Review evidence

The initial code review/debugging phase established the original root causes before implementation. A later findings-first diff review caught an incorrect first Task 3 approach that would have weakened Supabase/Control Center discovery; the implementation was corrected to suppress only the persistent GitHub provider's pre-lifespan upstream discovery. A compatibility pass also preserved the pre-existing positional order of `ProviderDescriptor` fields by appending the optional runtime-tool probe after existing fields.

No additional blocking static finding remains from the reviewed diff. One runtime-specific residual area remains unverified: Windows event-backed process-stream draining, including final tail delivery on process shutdown, requires executable evidence.

## Governance scope correction

The first governed worktree check after implementation failed with `PATH_OUTSIDE_CLAIM: tests/providers/test_runtime_tool_surface.py`. The file is part of Task 3 runtime-refresh verification and was changed by PR #76, but it was missing from `scope.json`. The owned-path claim has now been corrected to include `tests/providers/test_runtime_tool_surface.py`. This was a governance metadata defect only; no lifecycle implementation was changed by that correction.

## Execution-path note

The repository-local KIS execution surface became unavailable before implementation began. The change artifacts and branch were registered first, but the local governed worktree could not be created or validated from this session. Implementation therefore proceeded on the dedicated remote branch through the authenticated GitHub connector rather than by editing `main`. This is not treated as equivalent to the repository worktree gate: `change-workflow.ps1 check` from `.work/worktrees/061-empty-process-preflight` remains mandatory before the claim can become `ready`.

## Executable evidence available

Pre-implementation live diagnostics on Windows reproduced the empty-array production failure for both configured instances and demonstrated the disposable pre-lifespan provider connection with an isolated FastMCP client. Those are RED/root-cause evidence only; they do not verify the current branch.

## Verification still required

The local KIS execution surface is not connected to this chat, and the connected GitHub surface exposes no workflow-dispatch operation. The repository's reusable Windows workflow does not automatically run for this PR. At the current remote head, GitHub still reports no pull-request workflow run. Therefore no GREEN, canonical verifier, Windows CI, or live OAuth commissioning claim is recorded.

Required next evidence on the exact final head:

1. Fast-forward the governed `.work/worktrees/061-empty-process-preflight` worktree to the current remote branch, then run `pwsh -NoProfile -File .\scripts\change-workflow.ps1 check` from it.
2. Focused tests:
   `C:\Projects\.kis-mcp\python-env\Scripts\python.exe -m pytest -q tests/test_startup_scripts.py tests/providers/test_client_runtime.py tests/providers/github/test_server.py tests/providers/test_runtime_tool_surface.py tests/capabilities/test_runtime_refresh.py`
3. `pwsh -NoProfile -File .\scripts\verify.ps1`
4. Exact-head Windows CI through the repository workflow when a dispatcher/runner is available.
5. One supervised `kis-op` OAuth startup/commissioning run proving visible sign-in/device fallback, one persistent GitHub MCP process, authenticated runtime readiness, and tunnel readiness after authentication.
6. Only after steps 1–5 pass: set the governed change ready, complete PR #76 merge/closeout, reconcile final evidence, and retain the worktree until the commissioned `kis-op` runtime has started successfully. Worktree cleanup must happen last.

Do not set `scope.json` to `ready`, merge PR #76, or claim completion until that current evidence passes. Do not remove the worktree before the successful supervised `kis-op` commissioning run. No permanent deletion or policy change is part of this slice.
