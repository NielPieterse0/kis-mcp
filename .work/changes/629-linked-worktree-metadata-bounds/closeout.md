# Closeout: Linked Worktree Metadata Bounds

## Implemented scope

- Split Git metadata validation into `maximum_control_bytes` and `maximum_collection_bytes`.
- Retained the small control bound for `.git`, `commondir`, `HEAD`, loose refs, and alternates.
- Routed active config files and `packed-refs` through the existing bounded Git-output budget.
- Added linked-worktree regressions for legitimate config and packed-refs above 4 KiB.

## Validation evidence

- Focused Discover regression suite: `tests/discover/test_git_reader.py` — 15 passed.
- Diff scope check: passed; changed paths remain within `scope.json`.
- Exact-source code-quality review: PASS, zero actionable findings.
- Exact-source safety-security review: PASS, zero findings.
- Source fingerprint before publication: `daeb41901040ec234d333f2014e111f16744546c7bb5cdc68d7487931935feac`.

## Publication and closeout

- Branch: `change/629-linked-worktree-metadata-bounds`.
- Publication uses the direct progressively-disclosed KIS GitHub action surface rather than the unavailable workflow-local `commit_change` helper.
- Exact GitHub PR-head CI, merge, registered default-branch refresh, runtime activation, commodity #289 verification, and governed merged-clean worktree cleanup are required before final closure.
