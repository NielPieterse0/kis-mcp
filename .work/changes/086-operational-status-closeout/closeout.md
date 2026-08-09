# Closeout: Operational Status Closeout

- **Change ID**: `086-operational-status-closeout`
- **Development level**: Small
- **Result**: implementation and repository verification passed

## Implemented scope

- Supabase now carries one process-local commissioning state shared by its provider builder and readiness probe.
- A successful call marks registered-project live verification only when `project_id` is registered and the discovered upstream operation is annotated read-only.
- Failed calls, targetless reads, mutations, and rejected project IDs do not mark the state.
- `kis_provider_status` reports `ready_registered_project_read` after that evidence exists in the current runtime; otherwise it remains pending or blocked by existing readiness rules.
- Remote runtime publishes its selected instance only in process-local environment state for the lifetime of `run_remote_instance`.
- `kis_health` reads only the selected launcher-owned `current.json` and upgrades `remote_mcp` only when schema, lifecycle, instance, endpoint, and listener PID match the current serving process.
- The existing local commissioning prefix is preserved; only the stale `external_tunnel_pending_configuration` suffix becomes `external_tunnel_ready`.
- Checked-in `settings/kis-mcp.settings.json` was not edited because active change 084 owns it.

## Review

- Direct review found no blocking correctness, policy, secret-handling, scope, or regression issue.
- Authorization semantics are unchanged; the new Supabase state is evidence after successful execution, not an authorization input.
- Tunnel evidence is fail-closed for reporting: absent, malformed, stopped, wrong-instance, wrong-endpoint, or wrong-listener state leaves the static value unchanged.

## Verification evidence

- RED proof: focused test initially failed because the runtime-evidence API did not exist.
- Focused regression: `python -m pytest -q tests\commissioning\test_operational_status.py tests\providers\supabase\test_supabase_routing.py tests\providers\supabase\test_supabase_server.py tests\test_remote_runtime.py` -> **31 passed, exit 0**.
- Scope: `pwsh -NoProfile -File scripts\change-workflow.ps1 check` -> passed; changed paths exactly matched 086 ownership.
- Whitespace: `git diff --check` -> passed.
- Canonical: `pwsh -NoProfile -File scripts\verify.ps1` -> **exit 0**.
- Canonical checks passed for line endings, configuration, locked interpreter, FastMCP 3.4.4, pytest 8.4.2, Python syntax (229 files), change governance, full pytest, and exact HR-001/HR-002/HR-003 verification.
- Two existing pytest cases were skipped by the repository suite; three existing key-value store stability warnings were emitted. Neither is introduced by 086.

## Specialist review limitation

- `review_change_with_agent` using the preferred NVIDIA NIM backend returned `AGENT_BACKEND_UNAVAILABLE` because that optional backend is unavailable.
- An explicit Codex CLI review attempt also returned `AGENT_BACKEND_UNAVAILABLE`.
- The repository review contract was therefore performed directly; no unavailable specialist result is represented as a pass.

## Live ChatGPT-side commissioning evidence

- Local `main` was fast-forwarded to verified implementation commit `081154eb94463f64704ce89dec0eee2a3958737b`; no push was performed.
- `kis-op` replacement run `20260809T1247347935671Z` reached `lifecycle=ready` with listener PID `712` and tunnel PID `33932`.
- Actual `kis_health` returned `ready=true` and `remote_mcp=local_http_discover_write_read_quarantine_verified_external_tunnel_ready`.
- After restart, actual `kis_provider_status` correctly reported Supabase `live_verified=pending_registered_project_read`.
- Actual `supabase_get_project_url` succeeded for registered project `mmxuicfrdalymczdapjq`.
- A subsequent actual `kis_provider_status` reported Supabase `live_verified=ready_registered_project_read`.
- GitHub and Supabase are ready; NVIDIA NIM remains the sole optional degraded provider because `NVIDIA_API_KEY` is absent.

## Recovery and final cleanup gate

- Recovery is a normal revert of the bounded 086 commits; no migration or persistent commissioning state is introduced.
- Process-local Supabase evidence resets on runtime restart and must be re-established by a successful registered-project read.
- The first same-process detached restart attempt was reclaimed with the old `kis-op` process tree; the independent operator relaunch then completed successfully. This is a launcher-ownership constraint, not a runtime commissioning failure.
- Scope status is now `closed`; governed cleanup runs only after this metadata commit is merged into `main`.
- Changes 040, 084, and 085 remain explicitly out of scope and untouched. No push to `origin/main` is part of this change.
