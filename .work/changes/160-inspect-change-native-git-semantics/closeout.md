# Closeout: Inspect Change Native Git Semantics

## Implemented scope

- Reproduced #273 with a disposable 200-file linked worktree: native Git reported 0 modified tracked files while the pre-fix KIS `inspect_change(source="working_tree")` reported 200.
- Proved the divergence is caused by KIS suppressing effective system/global line-ending configuration (`core.autocrlf=true` in the reproducer), not by stale/shared Discover state, linked-worktree metadata, index selection, or #278 state ownership.
- Added a bounded read-only native Git config probe for effective `core.autocrlf` and `core.eol` semantics.
- Replayed only validated/canonicalized line-ending values into the existing isolated worktree `diff`/`status` evidence commands; arbitrary system/global config remains disabled for evidence execution.
- Preserved repository `.gitattributes`, external-diff/textconv suppression, credential/prompt isolation, output limits, total Git deadlines, and source-race guards.
- Added linked-worktree regressions for clean CRLF state, staged/unstaged/untracked inventory equivalence, repository attributes, Git hardening, and valid autocrlf boolean forms.

## Validation evidence

- Pre-fix regression: native `git diff --name-only` count `0`; current KIS `inspect_change` count `200` on the same linked worktree/index/HEAD.
- Test-first evidence: the two new linked-worktree regressions failed against the old behavior with false CRLF-only modifications, then passed after the fix.
- Affected Discover suite: `256 passed, 1 skipped` with `PYTHONPATH` pinned to this worktree's `src`.
- Canonical repository verification: `C:\Projects\.kis-mcp\python-env\Scripts\python.exe scripts\verify.py` completed with repository line endings, configuration, interpreter, dependencies, Python syntax, change governance, full pytest, and service verification all `ok: true`.
- Ruff: all changed Python files passed.
- `git diff --check`: passed.
- `pwsh -NoProfile -File scripts/change-workflow.ps1 check`: passed with only declared change-160 paths.

## Review

- NVIDIA `super` code-quality review timed out without a result; no mutation was possible because the operation was read-only.
- NVIDIA `nano` review completed and raised one claimed high finding that `_native_config_environment()` suppresses `GIT_CONFIG_SYSTEM`/`GIT_CONFIG_GLOBAL`. That finding was disproven: the native-probe environment preserves those variables, while only the subsequent isolated evidence environment replaces them with `os.devnull`. Focused hardening tests assert both sides explicitly.
- Local review identified valid Git boolean aliases/empty-value normalization as a compatibility edge; the implementation now canonicalizes supported boolean forms and uses Git's boolean parser for the ambiguous empty-value case.
- No unresolved #273 code-review finding remains.

## Git and merge

- Branch: `change/160-inspect-change-native-git-semantics`
- Worktree: `.work/worktrees/160-inspect-change-native-git-semantics`
- Commit: pending final governed commit
- Pull request or merge: pending
- Cleanup: pending merge

## Residual items

- #278 stale/shared state is not causal for #273 based on the exact reproducer; no #278 dependency is required for this fix.
- #265 remains a separate active lane. During verification, the shared editable Python environment was observed switching between worktree sources; final test evidence was therefore pinned explicitly to change 160, and the final repository verifier itself pins pytest to its own `src`.
