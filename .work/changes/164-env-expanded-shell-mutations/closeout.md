# Closeout: Env Expanded Shell Mutations

## Implemented scope

- Preserve syntactically definite unresolved write, entry, and delete mutation targets instead of dropping them during static path resolution.
- Carry unresolved mutation evidence through nested/wrapped shell parsing in `InvocationEffects` without changing the positional meaning of its original fields.
- Reject unresolved definite mutation targets structurally as `INVALID_INVOCATION_PATH` with no HR rule attribution; structural invalid-invocation evidence precedes HR attribution in mixed-effect cases.
- Preserve the existing targetless `unresolved_delete` signal and HR-003 behavior for destructive operations such as `git clean`.
- Recognize cmd `%VAR%` and modifier expansion, PowerShell environment/ordinary/scoped variables and subexpressions, including active expansions between adjacent quoted/unquoted argument fragments, while preserving literal percent paths and wholly single-quoted PowerShell marker paths.
- Track cmd delayed `!VAR!` expansion across one-shot and persistent shells. Honor the last `/V:ON` or `/V:OFF` wrapper switch before `/c` or `/k`; payload `/V:` text does not alter modeled wrapper state.
- Preserve the trust-model boundary that unknown commands and generic uncertainty alone do not create blockable mutation evidence.

## Validation evidence

- Focused parser/policy/provider/middleware/process-state/shell-parser verification: **143 tests passed**, with explicit `PYTEST_EXIT=0`.
- Ruff: PASS on all changed Python source/test files using the available repository-compatible Ruff executable.
- Diff integrity: `git diff --check` PASS.
- Governed scope check: PASS; exactly 14 owned files are changed, limited to change artifacts, four source files, and five focused test files.
- Local empirical cmd precedence check: `cmd.exe` confirms the last `/V` switch before `/c` wins (`/V:ON /V:OFF` leaves `!VAR!` literal; `/V:OFF /V:ON` expands it).
- Canonical exact-head verification: pending PR publication; GitHub Actions remains the canonical merge gate.

## Review

- Iterative code/security review findings were fixed in-scope: PowerShell variable case/general forms, literal percent handling, PowerShell quote/escape and adjacent-fragment handling, cmd modifier/non-identifier expansion, delayed expansion state, nested `/V:OFF` override, wrapper-vs-payload switch boundaries, and structural-vs-HR precedence.
- Final code-quality, safety-security, architecture, and API-contract rubrics were applied to the stabilized exact diff using the repository-approved manual fallback. No remaining blocking finding was identified.

## Review fallback evidence

- The configured Codex reviewer violated its read-only contract and repeatedly amended the change while the review wrapper correctly reported mutation detection; the surviving reviewer process tree was terminated before final verification.
- NVIDIA NIM review attempts exceeded their deadlines without returning usable evidence. Neither failed automated path was counted as a pass.
- The final stabilized tree was re-reviewed manually against code-quality, safety-security, architecture, and API-contract concerns, then independently reverified with the 143-test focused surface, Ruff, scope check, diff integrity, and the original `InvocationEffects` positional constructor contract.

## Git and merge

- Branch: `change/164-env-expanded-shell-mutations`.
- Worktree: `.work/worktrees/164-env-expanded-shell-mutations`.
- Base authority at change creation: `9d23a2026c04f30c0a963d315d12af6bee7ce1df`.
- Implementation commit: pending final exact-source review and governed commit.
- Pull request: pending governed publication.
- Merge: prohibited until exact-head Canonical Verification and merge-readiness gates pass.
- Cleanup: pending verified merge, runtime recommissioning, and issue closure.

## Residual acceptance gates

- Commit and publish only that reviewed source through registered KIS/GitHub operations.
- Require exact-head Canonical Verification success and merge-ready Work Management traceability.
- Merge only the frozen reviewed head, refresh `main`, restart/rebind the live runtime to the landed revision, and confirm KIS health.
- Verify #288 is closed with landed evidence, then safely remove the merged worktree/branch.
