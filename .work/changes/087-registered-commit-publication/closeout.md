# Closeout: Registered Commit Publication

## Implemented scope

- Added three KIS-owned exact registered-GitHub virtual operations: immutable commit publication, exact-head pull-request merge, and exact-head non-default remote-branch deletion.
- Bound every target to `settings/projects.settings.json`; no arbitrary repository, shell, `gh api`, admin bypass, token read, or force-history rewrite surface was added.
- Added JSON-governed `settings.github_cli.config_dir`; it must remain beneath `C:\Projects`, outside the repository, and is passed only as process-scoped `GH_CONFIG_DIR`.
- Registered the operations through the existing `execute_external_action` capability surface without expanding the bounded 24-operation direct profile.

## Validation evidence

- Focused integrated checks: 40/40 passed, including exact publication/merge/delete behavior, approval hardening, configuration validation, capability registration, and the fresh-process provider import-isolation regression.
- Repository verification: canonical `scripts/verify.ps1` passed on the exact integrated 087 head with full pytest exit 0, two expected skips, 246 Python files, 78 governance claims, and passing configuration/interpreter/dependency/syntax/line-ending checks.
- Diff scope check: `scripts/change-workflow.ps1 check` passed with only declared 087 paths.

## Review

- The configured external code-review backend was attempted and returned `AGENT_BACKEND_UNAVAILABLE`; it produced no findings and was not treated as review evidence.
- Direct diff review found no blocking defect in registered-target bounding, exact-SHA/ref-lease semantics, command construction, credential handling, approval enforcement, default-branch protection, or post-mutation verification.
- One real pre-commissioning defect was found and fixed test-first: the implementation initially pointed `GH_CONFIG_DIR` at a nonexistent state directory. Canonical JSON now points to the existing authenticated CLI state under `C:\Projects\.mcp-external-state\gh-config` and validates that boundary.

## Git and merge

- Branch: `change/087-registered-commit-publication`
- Worktree: `.work/worktrees/087-registered-commit-publication`
- Implementation commit: `cd549a0` (`feat: add exact registered GitHub operations`).
- Documentation commit: `3682c49` (`docs: document exact registered GitHub operations`).
- Latest integrated verification head includes final 085 closeout and current `main`; local merge/publication evidence remains to be recorded below.
- Cleanup: pending final live publication/commissioning and exact-head `main` verification.

## Residual items

- Live commissioning must prove the freshly loaded KIS surface can publish the exact final local `main` commit and verify GitHub `main` at that same SHA.
- Stale merged remote/local change branches will be removed only with exact-head evidence and normal non-force cleanup; unmerged or recovery branches will be preserved.
