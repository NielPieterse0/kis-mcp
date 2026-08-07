# Tasks: Startup and Control Center Closeout

- [x] Load repository authority, MCP skills, modularity-assessment, Superpowers, guardrails, and PR-completion guidance.
- [x] Confirm existing 077 worktree/branch and preserve pre-existing Control Center edits.
- [x] Trace the HTTP smoke failure to `stateless_http=False` in `remote_runtime.py`.
- [x] Trace startup unlock to secrets-launcher/vault coupling and confirm no production runtime consumer uses the active SecretsService.
- [x] Confirm the tunnel client accepts only `env:` or `file:` control-plane key references.
- [x] Confirm per-user Windows Credential Manager helper remains available and prior promptless startup used it safely.
- [x] Expand and validate change 077 scope without claiming paths owned by parallel change 078.
- [x] Task 1 — add failing Control Center render regression and implement concise local-only commissioning UI.
- [x] Task 2 — add failing stateless-runtime regression and honor JSON transport flags.
- [x] Task 3 — add failing startup regressions, restore one-time Windows tunnel credential storage, and remove runtime vault unlock.
- [x] Task 4 — update unclaimed documentation and change records.
- [x] Run focused tests and architecture/modularity checks.
- [x] Run change-governance check and canonical repository verification.
- [x] Review final diff and resolve advisory findings.
- [x] Commit/push and create or update PR #88.
- [ ] Reach PR `ready` state and obtain exact-head landing confirmation.
- [ ] Merge through the approved PR-completion landing path.
- [ ] Clean the merged change worktree/branch through `change-workflow.ps1 cleanup`.
