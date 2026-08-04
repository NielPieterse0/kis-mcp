# P1 Boundary Hardening Closeout

## Status

Implementation complete and awaiting pull-request review. The branch must not be merged without explicit operator approval.

## Implemented scope

- Added one bounded Git invocation context resolver for global `-C`, `--git-dir`, `--work-tree`, configuration overrides, mutation locations, remote precedence, `pushurl`, and explicit `--repo` targets.
- Added narrow CMD and PowerShell command segmentation with escape handling, grouping, invocation/script-block support, and sequential working-directory transitions.
- Added PID-scoped in-memory process state. State is recorded or updated only after successful provider calls and cleared after supported exit or termination evidence.
- Hardened GitHub search authorization with a bounded Boolean parser. Safe grouping, filters, nested filter disjunctions, and exclusions remain available; parser limitations and repository-scope violations have separate reasons and error codes.
- Added Discover Git metadata-graph validation for paths that the fixed read-only inspection actively loads or may traverse. Harmless remote URLs, inactive conditional includes, disabled worktree configuration, and passive alternates in unborn repositories remain usable.
- Closed the stale merged change claims for Discover 005 and GitHub provider 008 so the active P1 slice could own those already-landed surfaces without overlapping live agents.

## Policy and operator approval

The policy remains exactly HR-001, HR-002, and HR-003. No executable denylist, command allowlist, package restriction, generic destructive-command rule, provider tool reduction, or fourth hard rule was added.

The operator explicitly approved the code-level P1 boundary checks before implementation. That approval is recorded in `spec.md` and is limited to this slice. Additional hard-coded blocks still require separate operator approval.

## Review

The implementation was tightened after review:

- GitHub search no longer rejects parentheses or safe `NOT` filters merely for parser simplicity. It rejects only unsupported or scope-bypassing structures and reports `unsupported_search_grammar` separately from `repository_scope_violation`.
- Discover rejects only active metadata reads or traversal that escape the configured boundary, rather than every passive external-looking configuration reference.
- Obsolete lexical Git and shell helpers were removed so each boundary has one active resolver path.
- Existing ordinary operations remain covered, including `git status`, `git log`, `git branch --all`, local-only remotes, inert URLs, escaped separators, and unknown or unresolved effects.

No unresolved Critical or Important issue was found in the final local diff review.

## Verification

Fresh verification on the final implementation state:

- Targeted P1 Work, middleware, GitHub scope, and Discover Git suites passed.
- `pwsh -NoProfile -File scripts/change-workflow.ps1 check` passed with all changed paths inside the registered scope.
- `pwsh -NoProfile -File scripts/verify.ps1` passed the locked environment and complete repository suite with two expected skips.
- Verification confirmed 57 Python files compile, 10 governance claims are valid, dependency versions are locked, and the configured policy contains only HR-001, HR-002, and HR-003.

## Recovery

Close the PR or revert the branch commit. No migration, credential change, remote data change, or persistent operator data change is introduced.

## Known governance history

The initial repository state contained stale `active` claims for already-merged changes 005 and 008. Their merged state was verified before changing those records to `closed`. Current governance verification passes.
