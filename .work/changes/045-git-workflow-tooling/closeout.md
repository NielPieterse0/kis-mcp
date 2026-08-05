# Closeout: Git Workflow Tooling

## Status

Implementation and PR hardening complete; exact-head verification, merge, and cleanup pending.

## Implemented scope

- Added `scripts/git-workflow.py` with three fixed-shape local JSON commands:
  - `diff-summary` for merge-base-aware commits, name-status, rename/copy provenance, numstat, binary state, aggregate counts, path filtering, and bounded file records;
  - `pr-readiness` for branch/base/head, clean/detached state, ahead/behind counts, governed change identity, scope evidence, blockers, and recommended actions;
  - `cleanup-preview` for registered managed worktrees, cleanliness, merge ancestry, long-path risk, eligibility, and exact blockers.
- Added `scripts/git-workflow.ps1` using the repository-managed Python environment with a bounded system-Python fallback.
- Added strict ref, path, change-ID, repository, limit, and Git-common-directory validation.
- Added combined streaming stdout/stderr bounds and a fixed 30-second timeout for new Git evidence calls; large output is drained without unbounded buffering.
- Hardened `cleanup_change_worktree` to use `core.longpaths=true` and return structured cleanup evidence.
- Added recoverable fallback behavior when Git removes worktree registration but leaves an intact directory:
  - move the remnant beneath `C:\Projects\.backup`;
  - refuse if registration remains;
  - never force-delete;
  - delete the local branch only after safe removal or recovery.
- Made cleanup preview independent of worktree list ordering by resolving the primary worktree from Git’s absolute common directory.
- Added focused tests and operator/agent documentation.
- Installed no package and changed no Tool, Provider, runtime composition, policy, or settings file.

## Verification

- Initial red cycle: 7 expected failures proving the missing CLI and cleanup behavior.
- Focused regression after implementation: 23 tests passed.
- Aggregate-count and limit-contract regression: 25 tests passed.
- Expanded PR-review hardening regression: 33 tests passed, covering:
  - streaming output limits;
  - structural invalid-repository errors;
  - copy provenance parsing;
  - path-filtered diffs;
  - detached and scope-violating readiness;
  - invalid cleanup IDs;
  - primary-worktree order independence.
- Real worktree smoke checks:
  - committed `diff-summary` returned the exact 11-file branch report;
  - committed `pr-readiness` returned `ready: true`, ahead 1, behind 0, clean, and scope passed;
  - dirty-state `pr-readiness` correctly reported `WORKTREE_DIRTY` and `BRANCH_NOT_AHEAD`;
  - `cleanup-preview` correctly classified active clean, dirty, and unmerged worktrees without mutation.
- Pre-hardening `scripts/change-workflow.ps1 check`: passed and reported only declared `045` paths.
- Pre-hardening `git diff --check`: passed.
- Pre-hardening `scripts/verify.ps1`: passed:
  - complete pytest suite passed with 2 expected skips;
  - 158 Python files passed syntax validation;
  - locked dependencies, interpreter, JSON/configuration, line-ending, change-governance, and exact HR-001/HR-002/HR-003 checks passed.
- Hardened working-tree verification passed:
  - complete pytest suite passed with 2 expected skips;
  - 158 Python files passed syntax validation;
  - governance, configuration, dependencies, line endings, whitespace, interpreter, and exact HR-001/HR-002/HR-003 checks passed.

## Review

- Security: all new Git calls use fixed argument arrays, `shell=False`, no stdin, strict validation, incremental bounded capture, and timeout handling.
- Accuracy: review found and fixed aggregate counts that initially covered only returned records; totals include omitted records while returned details remain bounded.
- Validation: review found and fixed non-positive output limits, missing repository paths, and invalid cleanup IDs so they fail through structural error contracts.
- Boundedness: PR review found post-process output checks that still fully buffered Git output; capture now shares one combined byte budget across stdout and stderr while continuing to drain safely.
- Cleanup safety: worktree remnants are moved only after Git registration is proven absent; retained registration stops cleanup without moving the directory or deleting the branch.
- Determinism: cleanup preview no longer assumes the primary worktree is the first porcelain entry.
- Compatibility: ordinary clean merged cleanup remains supported; existing callers may ignore the new return value, while the CLI emits richer JSON.
- Modularity: local evidence and cleanup remain repository scripts. Remote PR mutations remain GitHub connector operations.
- Governance reuse: `pr-readiness` delegates scope evaluation to the existing authoritative change-governance checker rather than duplicating its ownership semantics.
- Findings: no critical or important findings remain after the PR-review fixes.

## Git and cleanup

- Branch: `change/045-git-workflow-tooling`
- Worktree: `.work/worktrees/045-git-workflow-tooling`
- Implementation commit: `8f64e279b4123e3e9cef24740b13db2440c334f8`
- Hardening commit: `c3d5faa54b176687575be248932120592146393d`
- Pull request: #57 — `Add structured Git workflow and recoverable cleanup commands`
- Merge: pending
- Cleanup: pending

## Residual boundaries

- The commands do not include uncommitted content in `diff-summary`; readiness separately reports dirty state.
- `cleanup-preview` performs no mutation and does not automatically clean unrelated worktrees.
- Remote push, PR creation, review, merge, and remote-branch deletion remain explicit connector actions.
- The authoritative scope check remains the existing change-governance implementation and therefore retains its established Git execution behavior.
