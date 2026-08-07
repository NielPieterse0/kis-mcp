# Change 061 closeout

## Status

Ready for landing. Tasks 1–5 are implemented. The repaired startup/auth lifecycle passed governed scope validation, focused regression tests, and the canonical verifier. Supervised live `kis-op` commissioning on `cba6cd0f6a08807f56050d7ed59a5c3d37970f06` completed one browser OAuth flow, reached `health=ready` and `tunnel_state=ready`, and subsequent authenticated GitHub user, private-repository, and pull-request reads reused the same runtime without another sign-in. A final reporting defect was then found: that proven runtime still exposed `commissioning.live_verified=not_verified`. RED/GREEN coverage now requires `live_verified=ready` whenever the shared startup state is ready; the reporting-only correction passed the required five-file focused suite (48 tests) and the canonical verifier. The final governed metadata head requires one exact-head Windows Work Management pass before merge.

## Implemented scope

- Empty process collections are valid startup preflight input and the startup PowerShell test helper now makes binder/runtime errors terminating.
- The persistent provider lifecycle owns startup state and a runtime tool snapshot; pre-lifespan upstream discovery is suppressed for that persistent provider, while `get_me` and initial discovery run inside the one shared client connection.
- GitHub readiness transitions to current-runtime authenticated state after startup succeeds and reports current-runtime live verification for the successful `get_me` plus upstream tool-discovery bootstrap; it does not claim persistent authentication across restarts or verification of every GitHub operation.
- Provider runtime tool snapshots are namespaced and fed into a capability catalogue/readiness view that refreshes at use time; the direct exposure profile remains fixed and bounded.
- Existing aggregate discovery for non-GitHub mounted providers is preserved.
- The launcher separates the supervised server/OAuth timeout from the fresh tunnel readiness timeout and drains retained server stderr live for OAuth/device-code guidance.
- `docs/OPERATIONS.md` is reconciled with the implemented lifecycle.

## Review evidence

The initial code review/debugging phase established the original root causes before implementation. A later findings-first diff review caught an incorrect first Task 3 approach that would have weakened Supabase/Control Center discovery; the implementation was corrected to suppress only the persistent GitHub provider's pre-lifespan upstream discovery. A compatibility pass also preserved the pre-existing positional order of `ProviderDescriptor` fields by appending the optional runtime-tool probe after existing fields.

No additional blocking static finding remains from the reviewed diff. Windows event-backed process-stream draining is now partially exercised by the successful OAuth/HTTP startup run; final retained tail delivery across normal long-running shutdown remains secondary to the current commissioning gate.

The first live commissioning run exposed one additional blocking runtime defect at endpoint ownership. Diagnostic process-tree evidence proved that `C:\Projects\.kis-mcp\python-env\Scripts\python.exe` is a Windows `uv` launcher which remains as the parent process while the real CPython child runs from the uv-managed interpreter location. Uvicorn owns port 8010 in that child. The previous assertion required the listener child itself to pass the canonical-launcher executable predicate, producing `KIS_MCP_ENDPOINT_OWNER_INVALID` after otherwise successful OAuth and MCP initialization. The repaired assertion validates the canonical selected server root and then requires the listener PID to be present in, and descend from, that newly created process tree. A focused regression failed on the old implementation and passed after the repair; final positive and negative ownership coverage is recorded in the executable evidence below.

## Governance scope correction

The first governed worktree check after implementation failed with `PATH_OUTSIDE_CLAIM: tests/providers/test_runtime_tool_surface.py`. The file is part of Task 3 runtime-refresh verification and was changed by PR #76, but it was missing from `scope.json`. The owned-path claim has now been corrected to include `tests/providers/test_runtime_tool_surface.py`. This was a governance metadata defect only; no lifecycle implementation was changed by that correction.

## Execution-path note
The canonical governed worktree is `C:\Projects\kis-mcp\.work\worktrees\061-empty-process-preflight`. The successful repeat commissioning runtime was launched from this canonical worktree and recorded that repository root in the operation `current.json`/startup-state evidence. The governed change remains anchored to the `.work/worktrees/...` path declared by `scope.json`.

## Executable evidence available
Current executable evidence is now substantial:

- On `cc9b08d`, `pwsh -NoProfile -File .\scripts\change-workflow.ps1 check` passed after the scope correction.
- On `cc9b08d`, the required focused regression set passed: 38 tests.
- On `cc9b08d`, `pwsh -NoProfile -File .\scripts\verify.ps1` passed, including governance, canonical interpreter/dependencies, Python syntax, full pytest, and the exact three-rule verification.
- The first supervised live `kis-op` run on 2026-08-07 completed GitHub browser OAuth (`github authorization complete`), started the FastMCP/Uvicorn HTTP server on `127.0.0.1:8010`, and served a successful MCP initialize request before stopping at endpoint ownership validation.
- Local process-tree diagnostics on the canonical environment showed the virtual-environment launcher process at `C:\Projects\.kis-mcp\python-env\Scripts\python.exe` with a descendant real CPython process under the uv-managed user interpreter path, confirming the listener-ownership mismatch mechanism.
- The new endpoint-owner regression failed against the old assertion with `KIS_MCP_ENDPOINT_OWNER_INVALID`, then passed after the root-plus-descendant repair. A negative regression also proves that a listener outside the selected server process tree is rejected with `KIS_MCP_ENDPOINT_OWNER_STALE`; the complete `tests/test_startup_scripts.py` file subsequently passed 26 tests.
- On the repaired implementation, `pwsh -NoProfile -File .\scripts\change-workflow.ps1 check` passed, the required five-file focused suite passed 40 tests, and `pwsh -NoProfile -File .\scripts\verify.ps1` passed the full repository suite.
- Exact-head Windows Work Management run #5 passed on `cba6cd0f6a08807f56050d7ed59a5c3d37970f06` before live commissioning.
- Repeat supervised commissioning on that exact head reached `health=ready` and `tunnel_state=ready`; preflight reclaimed zero stale server and tunnel processes; GitHub OAuth completed once; `kis_provider_status` reported authenticated/upstream/tool-discovery readiness; authenticated user, private-repository file, and PR reads then succeeded without another OAuth prompt.
- The final reporting-only correction was developed RED/GREEN: the new assertion failed while `live_verified` was `not_verified`, then passed after the readiness mapping was corrected. The required five-file focused suite then passed 48 tests and the canonical verifier passed again.
- The Codex CLI review backend was requested for the final reporting delta but was unavailable (`AGENT_BACKEND_UNAVAILABLE`); no claim of a Codex review pass is made.

## Landing and closeout

Exact-head Windows Work Management run #7 passed on final PR head `f234f5e48fc57c17fe106e558909a4d2513d35f7`. PR #76 was moved out of draft with no review threads and clean mergeability, then merged on 2026-08-07 as GitHub merge commit `57f314caa959ae40d9dec57f911d26eea78d785f`. Local `main` was updated from the verified equivalent governed branch tree and is subject to the canonical post-merge verifier before cleanup. The claim is now `closed`; governed cleanup may remove only the merged clean 061 worktree and local branch. No policy change or permanent artifact deletion is part of this slice.
