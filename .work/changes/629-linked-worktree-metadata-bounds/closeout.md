# Closeout: Linked Worktree Metadata Bounds

## Implemented scope

- Split Git metadata validation into `maximum_control_bytes` and `maximum_collection_bytes`.
- Retained the small control bound for `.git`, `commondir`, `HEAD`, loose refs, and alternates.
- Routed active config files and `packed-refs` through the existing bounded Git-output budget.
- Added linked-worktree regressions for legitimate config and packed-refs above 4 KiB plus fail-closed coverage above the collection budget.

## Verification and review

- Focused Discover regression suite: `tests/discover/test_git_reader.py` — 15 passed.
- Diff scope check: PASS.
- Exact-source code-quality review: PASS, zero actionable findings.
- Exact-source safety-security review: PASS, zero findings.
- Pre-publication source fingerprint: `daeb41901040ec234d333f2014e111f16744546c7bb5cdc68d7487931935feac`.
- Local immutable source commit: `98734b8418442db447d1519a53f8b827776eb5cf`.
- Reconciled PR head: `63e1e15d152de86c13ef02ffd1020e9bf3e8aa98`.
- Canonical GitHub Actions run `33744067009` passed exact-head repository verification.

## Publication and post-merge proof

- PR #676 merged successfully.
- Merge/default-branch SHA: `e61c7a8c889e9dd90e276b1c951eeec13b6b03e3`.
- Registered default-branch tracking was refreshed to the exact merge SHA.
- Live merged KIS `inspect_project` against `C:\Projects\commodity` now reports Git available, repository true, branch `main`, clean status, and no Git metadata diagnostics. This clears the KIS infrastructure blocker affecting commodity #289; #289 remains open because its separate scientific acceptance criteria are not completed by this infrastructure fix.
- Incorrect blocker report kis-mcp #674 was corrected and closed as `not_planned` after progressive direct actions proved publication was available.
- The clean #629 worktree was removed after confirming its entire owned scope is byte-equivalent to merged `main`. The retained remote review branch follows KIS closeout policy.

## Final state

Change `629-linked-worktree-metadata-bounds` is closed. Implementation, exact-head CI, merge, default-branch refresh, live commodity verification, issue correction, and worktree cleanup are complete.
