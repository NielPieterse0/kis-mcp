# Closeout: kis-mcp Skill Refresh

## Implemented scope

- Refreshed the repository-local `kis-mcp` skill around a task-first fast path so common health, project, repository, change, verification, review, validation, and closeout intents reach the smallest useful KIS surface.
- Added current change-workflow guidance for `inspect_change`, `analyze_change`, `plan_change`, `select_change_verification`, `run_verification`, and live-advertised `execute_change_workflow` / `execute-current-change`.
- Added current Python quality evidence semantics for Ruff, coverage.py/pytest-cov, Vulture, LibCST, mypy, and Pyright without implying installation or automatic execution.
- Added all seven fixed specialist review purposes and bounded agnix validation guidance.
- Reconciled central project registry, Supabase account OAuth, current startup secret handling, Govern advisory availability, and safe registered-GitHub closeout guidance.
- Recorded locally merged Slice 6 reconciliation and the active Slice 7 change 106 contract: planned `prepare_reviewable_pull_request` verifies an exact commit, publishes it through registered exact GitHub operations, creates/verifies an open reviewable PR, and stops before merge/delete/cleanup; live discovery remains required before invocation.

## Validation evidence

- Structural skill check: 253-line `SKILL.md`, six referenced files resolved, canonical LF on the skill package.
- `pwsh -NoProfile -File .\scripts\change-workflow.ps1 check`: passed for all 11 declared paths.
- `git diff --check`: passed.
- Canonical `pwsh -NoProfile -File .\scripts\verify.ps1`: passed; pytest exit 0 with two expected skips, 264 Python files syntax-checked, line endings/configuration/interpreter/dependencies/change-governance and exact HR-001/002/003 checks green.

## Review

- Manual requirements/diff review found no blocking scope, authority, factual-status, progressive-disclosure, or usability issue.
- Codex documentation review failed before findings with `AGENT_BACKEND_FAILED:CodexCliError`; no Codex pass is claimed.
- NVIDIA NIM `super` documentation review failed before findings with `AGENT_BACKEND_FAILED:NvidiaNimError`; no NVIDIA pass is claimed.

## Git and merge

- Branch: `change/105-kis-mcp-skill-refresh`.
- Worktree: `.work/worktrees/105-kis-mcp-skill-refresh`.
- Verified implementation commit: `b1c403bb3d7ae9908290ea368f73d7a90790ba55`.
- Lifecycle reconciliation commit: `752ae140fd576174c3babb62f9d466a50f83135f`.
- Final Slice 7 contract-alignment commit: this final verified change commit.
- Delivery target: local `main`; no remote publication is required by this documentation-only request.
- Final merge/cleanup is evidenced by Git/worktree state and `change-workflow cleanup` output rather than a recursive post-cleanup metadata edit.

## Residual items

- Slice 7 remains the separate active `106-reviewable-pr-coordinator` implementation. This skill documents its declared operator boundary and live-discovery gate; change 105 does not implement or alter that coordinator.
- A running kis-op/kis-dev process may lag the checked-out repository. Live capability and schema evidence remains authoritative for invocation availability.
