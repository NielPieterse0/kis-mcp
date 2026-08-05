# Closeout: Git Workflow Tooling

## Status

Implementation and local review complete; publication, merge, and cleanup pending.

## Implemented scope

- Added `scripts/git-workflow.py` with three fixed-shape local JSON commands:
  - `diff-summary` for merge-base-aware commits, name-status, rename/copy provenance, numstat, binary state, aggregate counts, path filtering, and bounded file records;
  - `pr-readiness` for branch/base/head, clean/detached state, ahead/behind counts, governed change identity, scope evidence, blockers, and recommended actions;
  - `cleanup-preview` for registered managed worktrees, cleanliness, merge ancestry, long-path risk, eligibility, and exact blockers.
- Added `scripts/git-workflow.ps1` using the repository-managed Python environment with a bounded system-Python fallback.
- Hardened `cleanup_change_worktree` to use `core.longpaths=true` and return structured cleanup evidence.
- Added recoverable fallback behavior when Git removes worktree registration but leaves an intact directory:
  - move the remnant beneath `C:\Projects\.backup`;
  - refuse if registration remains;
  - never force-delete;
  - delete the local branch only after safe removal or recovery.
- Added focused tests and operator/agent documentation.
- Installed no package and changed no Tool, Provider, runtime composition, policy, or settings file.

## Verification

- Initial red cycle: 7 expected failures proving the missing CLI and cleanup behavior.
- Focused regression after implementation: 23 tests passed.
- Tightened aggregate-count and limit-contract regression: 25 tests passed.
- Real worktree smoke checks:
  - `pr-readiness` correctly reported `WORKTREE_DIRTY` and `BRANCH_NOT_AHEAD` while passing the registered scope check;
  - `cleanup-preview` correctly classified active clean, dirty, and unmerged worktrees without mutation.
- `scripts/change-workflow.ps1 check`: passed and reported only declared `045` paths.
- `git diff --check`: passed.
- `scripts/verify.ps1`: passed:
  - complete pytest suite passed with 2 expected skips;
  - 158 Python files passed syntax validation;
  - locked dependencies, interpreter, JSON/configuration, line-ending, change-governance, and exact HR-001/HR-002/HR-003 checks passed.

## Review

- Security: all Git calls use fixed argument arrays, `shell=False`, no stdin, strict ref/path validation, and bounded output.
- Accuracy: review found and fixed aggregate counts that initially covered only returned records; totals now include omitted records while returned details remain bounded.
- Validation: review found and fixed non-positive output limits so they fail with `GIT_LIMIT_INVALID` rather than a misleading output-limit error.
- Recovery: worktree remnants are moved only after Git registration is proven absent; retained registration stops cleanup without moving the directory or deleting the branch.
- Compatibility: ordinary clean merged cleanup remains supported; existing callers may ignore the new return value, while the CLI now emits richer JSON.
- Modularity: local evidence and cleanup remain repository scripts. Remote PR mutations remain GitHub connector operations.
- Findings: no critical or important findings remain.

## Git and cleanup

- Branch: `change/045-git-workflow-tooling`
- Worktree: `.work/worktrees/045-git-workflow-tooling`
- Implementation commit: pending
- Pull request: pending
- Merge: pending
- Cleanup: pending

## Residual boundaries

- The commands do not include uncommitted content in `diff-summary`; readiness separately reports dirty state.
- `cleanup-preview` performs no mutation and does not automatically clean unrelated worktrees.
- Remote push, PR creation, review, merge, and remote-branch deletion remain explicit connector actions.
