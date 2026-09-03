# Closeout: Pytest Asyncio Local Collection

## Implemented scope

- Added `scripts/test.ps1` as the supported local pytest entrypoint using `C:\Projects\.kis-mcp\python-env\Scripts\python.exe`.
- The entrypoint sets `PYTHONNOUSERSITE=1` so incompatible ambient user-site pytest plugins cannot participate, without disabling pytest plugin autoload.
- Pytest arguments and exit codes are forwarded unchanged.

## Validation evidence

- Focused repository-scope tests passed.
- Behavioral wrapper test passed, including managed-interpreter selection, user-site isolation, plugin-autoload preservation, argument forwarding, and exit-code propagation.
- Full repository collection through `scripts/test.ps1 --collect-only -q tests` succeeded.
- `scripts/change-workflow.ps1 check` and `git diff --check` passed.

## Review

- Initial review requested behavioral coverage instead of source-text assertions.
- Behavioral coverage was added; final Codex code-quality re-review returned zero findings.

## Git and merge

- Branch: `change/636-pytest-asyncio-local-collection`
- Worktree: `.work/worktrees/636-pytest-asyncio-local-collection`
- Commit: pending.
- Pull request or merge: pending.
- Cleanup: pending.

## Residual items

- None in scope.
