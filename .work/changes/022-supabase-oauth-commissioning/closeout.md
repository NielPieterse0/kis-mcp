# Closeout: 022-supabase-oauth-commissioning

## Status

Implementation complete and verified. Pull request #23 is open and cleanly mergeable. Operator browser commissioning remains pending because `SUPABASE_PROJECT_REF` is not present in the current process environment.

## Outcome

The Supabase provider now uses the official hosted endpoint through OAuth 2.1 dynamic client registration. OAuth client and token state use Windows Credential Manager through the configured `kis-mcp/supabase` keyring service. Runtime no longer accepts or forwards a PAT.

The adapter preserves mandatory project scoping, constructs the official project-scoped URL, reports redacted OAuth preflight state, and mounts through the existing shared provider runtime. Explicit commissioning and shared smoke verify the expected project-scoped surface and invoke only `get_project_url`; account-level tools are rejected, and read-only/read-write surface differences are checked without invoking mutations.

## Governance

The primary `main` worktree was not modified. Slice C remained confined to its declared worktree and owned paths. Stale merged claims `009-supabase-mcp-provider` and `017-p2-operational-hardening` are closed so governance validation no longer reports false overlap with current Supabase ownership.

## Verification

Completed evidence:

- 60 focused Supabase tests passed with `uv run --offline --no-sync` and the Slice C `PYTHONPATH`.
- Strict JSON validation passed for provider settings, provider schema, and Slice C scope.
- `scripts/change-workflow.ps1 check` passed for all changed paths.
- `git diff --check` passed after normalizing changed files to LF.
- Local preflight passed as a command and reported `token_storage_available=true`, `legacy_pat_conflict=false`, and `project_ref_present=false`.
- Full `scripts/verify.ps1` passed: 510 tests passed, 2 expected skips, 74 Python files passed syntax validation, 18 governance claims validated, FastMCP 3.4.4 and pytest 8.4.2 matched the lock.

The full verifier synchronized the shared editable Python environment to this worktree; no concurrent verification was run.

## Live commissioning

Not executed. The current process has no `SUPABASE_PROJECT_REF`, so the implementation correctly reports preflight as incomplete and prevents browser/live modes from starting without an explicit development or test project scope.

Required operator sequence:

```powershell
$env:SUPABASE_PROJECT_REF = '<development-project-ref>'
Remove-Item Env:SUPABASE_ACCESS_TOKEN -ErrorAction SilentlyContinue
pwsh -File .\scripts\auth-supabase-mcp.ps1
pwsh -File .\scripts\smoke-supabase-mcp.ps1 -SharedRuntime
```

These workflows perform no Supabase mutation.

## Recovery

Stop provider processes, revoke the Supabase authorization when appropriate, remove the `kis-mcp/supabase` entries through Windows Credential Manager, rerun explicit commissioning, and repeat the shared-runtime smoke. No plaintext credential fallback is implemented.
