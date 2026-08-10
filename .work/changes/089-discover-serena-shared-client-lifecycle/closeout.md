# Closeout: Discover Serena Shared Client Lifecycle

## Implemented scope

- Root cause: FastMCP proxy discovery re-entered the same `_SharedProviderClient`; the nested exit cleared Serena's published client while the outer persistent lifespan remained ready.
- Added context-depth ownership so nested proxy contexts retain the active Serena client/event loop and only the outermost exit clears them.
- Added a regression covering outer entry, nested entry/exit retention, and final outer-exit clearing.
- Implementation commit: `48fa1994f15c11fb5205bbfbe704f96f6e1a61ab`.
- Integrated by fast-forward into local `main` at the same SHA before live commissioning.

## Verification evidence

- RED regression failed exactly because `adapter._active_client` became `None` after nested exit.
- GREEN regression passed after the minimal lifecycle change.
- Focused Serena/provider/Discover suite: 55/55 passed.
- Governed scope check passed with only declared 089 paths.
- Canonical pre-integration `scripts\verify.ps1`: pytest 100%, exit 0, two expected skips, 246 Python files, 80 governance claims, and all configuration/interpreter/dependency/syntax/line-ending checks passed.

## Live commissioning

- Fresh `kis-dev` reached `ready` from integrated primary `main` on `127.0.0.1:8011`.
- Fresh `inspect_project` generated/refreshed persistent intelligence for clean head `48fa1994...` with semantic provider `serena-mcp` 1.6.1 `available=true`; the previous independent semantic RuntimeError is absent.
- Serena remains offline-enforced and central project state remains outside the repository.
- Provider live smoke passed: Context7 local startup/tool discovery; Serena semantic reads; memory quarantine/restore; restart verification; `repo_local_state_absent=true`.
- GitHub Project inventory still resolves issue #102 and reconciliation preview for `Status=Done` returns `noop`, `success=true`.
- Work write/read succeeded; direct permanent-delete intent returned `HR-003_QUARANTINE_REQUIRED`; the smoke file was then recoverably quarantined as `20260810T073519843646Z-9002470556a5`.
- `kis_provider_status` reports Serena, GitHub, Supabase, Context7, Desktop Commander, and Control Center ready; platform aggregate remains degraded only because optional NVIDIA NIM lacks `NVIDIA_API_KEY`.

## Review

- Direct review confirmed no changes to provider schemas, Serena public exposure, offline enforcement, project-state location, Discover persistence contracts, or HR-001/HR-002/HR-003.
- No blocking findings remain.

## Post-closeout procedure

- Fast-forward this metadata-only closeout commit into `main`.
- Run canonical `scripts\verify.ps1` on that exact primary head.
- Publish only that verified SHA through `kis_github_publish_registered_commit` using the exact observed GitHub `main` base.
- Independently verify remote `main`, reconcile local `origin/main`, and run governed cleanup for 089 without force deletion.
- Restart `kis-dev` from the exact final published `main` and confirm health/runtime identity after cleanup.

## Preserved residuals

- Preserve local `recovery/080-local-divergent`, remote `automation/047-publish-temp`, and remote `change/007-chatgpt-remote-commissioning`; prior patch-equivalence audits found unique content, so they are not cleanup candidates.
