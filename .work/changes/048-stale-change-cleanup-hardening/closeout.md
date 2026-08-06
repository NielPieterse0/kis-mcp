# Closeout: Stale Change Cleanup Hardening

## Status

Implementation and local review are complete. The claim is closed so its closure metadata can be merged before governed cleanup.

## Root cause

`scripts/change-governance.py cleanup` verified worktree cleanliness and merge ancestry but did not require the change claim to be `closed`. It could therefore remove a merged worktree and local branch while the authoritative `scope.json` on `main` still said `active`.

## Implemented scope

- Cleanup now rejects `active` and `ready` claims with `CHANGE_STATUS_NOT_CLOSED`.
- Cleanup still requires a clean worktree and branch ancestry in the declared base.
- `cleanup-preview` reports the same closure blocker and cannot advertise a non-closed claim as eligible.
- Existing recoverable long-path fallback and non-forced branch deletion behavior remain unchanged.
- Regression tests cover active, ready, closed, merged, unmerged, dirty, recovery, and retained-registration paths.

## Historical reconciliation

- Change `041-dual-instance-commissioning` is marked `closed`; PR `#50`, reviewed head `6cc54e0abf613811c1244252e33fb259baf9750f`, and merge `af81d2fdc16ae84635438852c6676654dced48c4` are recorded.
- Change `046-modularity-hardening` is marked `closed`; PR `#59`, reviewed head `53cdebb71fb4ee521b59eba352fd7d6881053ed5`, and merge `f4475961c44634b17327a934031f98bacc12d3d7` are recorded.
- Both reviewed heads and merge commits are ancestors of `main`; their local branches and worktrees are absent.
- Reconstruction is unnecessary because all tracked artifacts remain in Git history and merged `main`.

## Verification evidence

- TDD RED: two cleanup tests failed because `active` and `ready` claims were incorrectly removed.
- TDD RED: cleanup preview incorrectly reported a merged `active` claim as eligible.
- TDD GREEN: `tests/test_change_governance.py` and `tests/test_git_workflow.py` passed, 38 tests total.
- `pwsh -NoProfile -File scripts/change-workflow.ps1 validate` passed with two active changes before this claim was closed.
- `pwsh -NoProfile -File scripts/change-workflow.ps1 check` passed with only declared paths.
- `git diff --check` passed.
- The NVIDIA review backend reported no implementation defect; its preview summary was manually corrected because preview adds a blocker rather than raising.
- The independently requested Codex review backend was unavailable (`AGENT_BACKEND_UNAVAILABLE`); direct diff review found no blocking issue.
- The exact PR head must also pass `pwsh -NoProfile -File scripts/verify.ps1`; that current result belongs in the PR and completion evidence.

## Protected concurrent work

- `040-context7-serena-adapters` remains untouched and retained.
- `047-capability-composition-and-tool-experience` remains untouched; it independently declares a dependency on change `048` and no longer claims the reconciled 041/046 paths.
- No policy, provider, runtime, credential, package, or external-state change is included.

## Recovery and cleanup

No permanent deletion is introduced or used. Git history preserves tracked artifacts. A failed worktree removal retains registration or moves an unregistered remnant beneath `C:\Projects\.backup`. After PR merge and merged-main verification, cleanup may remove only the clean merged `048` worktree and its local branch through the governed command.
