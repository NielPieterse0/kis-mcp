# Closeout: 022-supabase-oauth-commissioning

## Status

Implementation, operator browser commissioning, and shared-runtime verification are complete. Pull request #23 remains open and unmerged pending final review and exact-head authorization.

## Outcome

The Supabase provider uses the official hosted endpoint through OAuth 2.1 dynamic client registration. OAuth client and token state use Windows Credential Manager through the configured `kis-mcp/supabase` keyring service. Runtime does not accept or forward a PAT.

The adapter preserves mandatory project scoping, constructs the official project-scoped URL, reports redacted OAuth preflight state, and mounts through the existing shared provider runtime. Explicit commissioning and shared smoke verify the expected project-scoped surface and invoke only `get_project_url`; account-level tools are rejected, and read-only/read-write surface differences are checked without invoking mutations.

Live commissioning exposed a Supabase DCR interoperability defect: the registration response returned a client secret but omitted `token_endpoint_auth_method`, causing the generic MCP client to omit the required secret during token exchange. The Supabase-specific OAuth adapter now requests `client_secret_post`, normalizes secret-bearing responses that return `null` or `none`, persists the corrected client record, and performs the token exchange with the secret.

## Governance

The primary `main` worktree was not modified. Slice C remained confined to its declared worktree and owned paths. Stale merged claims `009-supabase-mcp-provider` and `017-p2-operational-hardening` are closed so governance validation no longer reports false overlap with current Supabase ownership.

## Verification

Completed evidence:

- 61 focused Supabase tests passed with the locked project interpreter and Slice C `PYTHONPATH`.
- The OAuth interoperability regression was observed failing before the adapter repair and passing afterward.
- Strict JSON validation passed for provider settings, provider schema, and Slice C scope.
- `scripts/change-workflow.ps1 check` passed for all changed paths.
- `git diff --check` passed.
- Local preflight reports Windows keyring availability and rejects missing project scope or a legacy PAT before network use.
- Live browser commissioning for an operator-supplied development/test project returned `authentication=true`, `project_scoped_read=true`, and `surface=true`.
- Live shared-runtime smoke returned `mounted=true`, `ready=true`, `authentication=true`, `project_scoped_read=true`, and `surface=true`.
- Full `scripts/verify.ps1` passed: 511 tests passed, 2 expected skips, 74 Python files passed syntax validation, 18 governance claims validated, and FastMCP 3.4.4 / pytest 8.4.2 matched the lock.

The full verifier synchronized the shared editable Python environment from the Discover worktree to this worktree; no concurrent verification was run.

## Live commissioning

Commissioning used an operator-supplied development/test project reference. The operator completed the browser authorization. Credentials are retained only in Windows Credential Manager; the project reference is process-scoped for launcher use and no key, password, connection string, PAT, OAuth token, client ID, or client secret was written to repository files.

The commissioning and shared-runtime workflows performed no Supabase mutation. FastMCP emitted upstream session-termination `404` cleanup warnings after successful calls, but both commands returned exit code 0 with complete positive evidence.

## Recovery

Stop provider processes, revoke the Supabase authorization when appropriate, remove the `kis-mcp/supabase` entries through Windows Credential Manager, rerun explicit commissioning, and repeat the shared-runtime smoke. No plaintext credential fallback is implemented.
