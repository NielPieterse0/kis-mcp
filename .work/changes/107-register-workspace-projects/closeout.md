# Closeout: Register Workspace Projects

## Implemented scope

- Added all eight requested local roots to the strict central registry.
- Added verified GitHub bindings for `chatgpt-skill`, `doc-solution`, `app-dev-core`, `mi-fi`, `prose2llm`, and `signal`.
- Registered `import-isolate` and `app-builder` as local-only because no matching accessible GitHub repository was found and neither requested root is a Git repository.
- Preserved the existing `college`, `commodity`, `gpt-os`, and `kis-mcp` definitions, the `kis-mcp` default, GitHub Project #1 binding, and Supabase binding.
- Updated only the existing exact registry/catalogue contract tests and change-lifecycle artifacts; no runtime source, provider settings, policy, or target-project files changed.

## Validation evidence

- Local/GitHub identity preflight completed for all eight requested roots.
- Focused registry suite: 10 passed.
- `pwsh -NoProfile -File scripts/change-workflow.ps1 check`: passed with only declared paths.
- `git diff --check`: passed.
- Canonical `pwsh -NoProfile -File scripts/verify.ps1`: passed; pytest exit 0 with two expected skips, 264 Python files syntax-checked, configuration/interpreter/dependencies/change-governance all green.

## Review

- `review_change_with_agent` with explicit Codex CLI/API-contracts purpose was attempted and failed with `AGENT_BACKEND_FAILED:CodexCliError`; no review result was represented as passed.
- Direct final review used `inspect_change`, full branch diff, focused tests, and canonical verification; no blocking finding, policy change, source-code change, or undeclared path was found.
- Known source drift is retained rather than silently repaired: `C:\Projects\ChatGPT-skill` still references the older `chatgpt-skill-adoption` repository locally, while current GitHub evidence identifies `NielPieterse0/chatgpt-skill`; KIS uses the current GitHub coordinate.

## Git and merge

- Branch: `change/107-register-workspace-projects`
- Worktree: `.work/worktrees/107-register-workspace-projects`
- Commit: one final bounded change/closeout commit is created after current-state verification; its SHA is reported by the integration step.
- Pull request or merge: local governed fast-forward integration to `main`; no remote publication was requested.
- Cleanup: governed worktree and branch cleanup follows the verified fast-forward merge.

## Residual items

- Running `kis-op` and `kis-dev` processes retain their startup registry snapshot and must be restarted after integration before `kis_list_projects` exposes the new projects.
- `import-isolate` and `app-builder` intentionally have no GitHub binding until a repository identity is explicitly established.
- Repairing the stale `ChatGPT-skill` local Git remote/AGENTS naming and initializing Git metadata under `signal` are separate target-project changes and remain out of scope.
