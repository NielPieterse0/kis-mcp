# Change 061 closeout

## Status

Active. Tasks 1–4 are implemented. The original governed scope check, focused regression suite, and canonical verifier passed on `cc9b08d`. The first supervised live `kis-op` run then completed GitHub OAuth and started the HTTP server, but correctly stopped before tunnel startup because endpoint ownership validation falsely rejected the Windows `uv` interpreter child that owned the Uvicorn listener. That commissioning defect is repaired locally with RED/GREEN regression evidence. On the repaired working state, governance passed, the required focused suite passed 40 tests, and the canonical verifier passed. Commit/push, exact-head Windows CI, and repeat live commissioning remain pending.

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

No additional blocking static finding remains from the reviewed diff. Windows event-backed process-stream draining is now partially exercised by the successful OAuth/HTTP startup run; final retained tail delivery across normal long-running shutdown remains secondary to the current commissioning gate.

The first live commissioning run exposed one additional blocking runtime defect at endpoint ownership. Diagnostic process-tree evidence proved that `C:\Projects\.kis-mcp\python-env\Scripts\python.exe` is a Windows `uv` launcher which remains as the parent process while the real CPython child runs from the uv-managed interpreter location. Uvicorn owns port 8010 in that child. The previous assertion required the listener child itself to pass the canonical-launcher executable predicate, producing `KIS_MCP_ENDPOINT_OWNER_INVALID` after otherwise successful OAuth and MCP initialization. The repaired assertion validates the canonical selected server root and then requires the listener PID to be present in, and descend from, that newly created process tree. A focused regression failed on the old implementation and passed after the repair; final positive and negative ownership coverage is recorded in the executable evidence below.

## Governance scope correction

The first governed worktree check after implementation failed with `PATH_OUTSIDE_CLAIM: tests/providers/test_runtime_tool_surface.py`. The file is part of Task 3 runtime-refresh verification and was changed by PR #76, but it was missing from `scope.json`. The owned-path claim has now been corrected to include `tests/providers/test_runtime_tool_surface.py`. This was a governance metadata defect only; no lifecycle implementation was changed by that correction.

## Execution-path note
The local KIS execution surface is now available to this chat and the canonical registered worktree is `C:\Projects\kis-mcp\.work\worktrees\061-empty-process-preflight`. The operator's first live commissioning command was run from a separate sibling checkout path shown in the console as `C:\Projects\kis-mcp.work\worktrees\061-empty-process-preflight`; that run was on `cc9b08d` and supplied valid runtime evidence, but the repaired branch must be pushed and that operator checkout must be fast-forwarded before the repeat live commissioning run. The governed change remains anchored to the canonical `.work/worktrees/...` path declared by `scope.json`.

## Executable evidence available
Current executable evidence is now substantial:

- On `cc9b08d`, `pwsh -NoProfile -File .\scripts\change-workflow.ps1 check` passed after the scope correction.
- On `cc9b08d`, the required focused regression set passed: 38 tests.
- On `cc9b08d`, `pwsh -NoProfile -File .\scripts\verify.ps1` passed, including governance, canonical interpreter/dependencies, Python syntax, full pytest, and the exact three-rule verification.
- The first supervised live `kis-op` run on 2026-08-07 completed GitHub browser OAuth (`github authorization complete`), started the FastMCP/Uvicorn HTTP server on `127.0.0.1:8010`, and served a successful MCP initialize request before stopping at endpoint ownership validation.
- Local process-tree diagnostics on the canonical environment showed the virtual-environment launcher process at `C:\Projects\.kis-mcp\python-env\Scripts\python.exe` with a descendant real CPython process under the uv-managed user interpreter path, confirming the listener-ownership mismatch mechanism.
- The new endpoint-owner regression failed against the old assertion with `KIS_MCP_ENDPOINT_OWNER_INVALID`, then passed after the root-plus-descendant repair. A negative regression also proves that a listener outside the selected server process tree is rejected with `KIS_MCP_ENDPOINT_OWNER_STALE`; the complete `tests/test_startup_scripts.py` file subsequently passed 26 tests.
- On the repaired working state after temporary diagnostics were removed, `pwsh -NoProfile -File .\scripts\change-workflow.ps1 check` passed.
- On that same repaired state, the required five-file focused suite passed 40 tests.
- On that same repaired state, `pwsh -NoProfile -File .\scripts\verify.ps1` passed the full repository suite, governance, canonical interpreter/dependencies, syntax checks, and exact three-rule verification.

These results do not yet close the slice because the production repair has not been committed/pushed, exact-head Windows CI is still required, and supervised commissioning must be repeated through tunnel readiness.

## Verification still required
Required next evidence on the repaired exact final head:

1. Commit and push the repaired branch and record the exact new head SHA.
2. Obtain exact-head Windows CI evidence for PR #76.
3. Fast-forward the operator commissioning checkout to that exact remote head and repeat one supervised `kis-op` startup. It must complete OAuth when required, validate endpoint ownership through the actual Windows process tree, reach `health=ready` and `tunnel_state=ready`, and keep the runtime open for authenticated GitHub capability verification.
4. Verify current runtime provider/capability status from ChatGPT against the running `kis-op` instance.
5. Only after steps 1–4 pass: set the governed change ready, update PR #76 from draft as appropriate, complete the repository's landing-confirmation flow, reconcile final evidence, and clean up the worktree last.

Do not set `scope.json` to `ready`, merge PR #76, or remove the worktree before successful repeat commissioning. No permanent deletion or policy change is part of this slice.
