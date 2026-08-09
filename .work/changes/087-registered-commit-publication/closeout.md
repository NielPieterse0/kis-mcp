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
- The verified 087 branch was fast-forwarded into local `main`; fresh `kis-dev` restart then exposed all three new operations as ready/eligible through capability discovery.
- First live exact publication succeeded: local `main` `2b8411371532b941921ef4d797d96ba183e4e69a` was published over expected remote base `489153044433b61ad127ca7c3b91bcc53f9d3a23`, and an independent GitHub provider read verified remote `main` at the exact target SHA.
- Exact registered-branch deletion was then commissioned across the full set of 28 remote branches independently proven merged into final local `main`; every deletion matched its expected head and returned that commit as the recovery SHA.
- Final remote inventory after cleanup contains only `main` plus four deliberately preserved branches not proven merged: `automation/047-publish-temp`, `change/007-chatgpt-remote-commissioning`, `change/079-workflow-discovery-bridge-dependency`, and `change/079-workflow-discovery-dependency-v2`.
- Cleanup: remote merged-branch cleanup is complete. Final local tracking/branch cleanup and publication of this closeout-only commit are performed from primary `main` after this record is committed.

## Residual items

- No implementation or commissioning item remains.
- Preserve the four unmerged remote branches above and local `recovery/080-local-divergent` until separately reconciled; they are not safe cleanup candidates in this closeout.
