# Closeout: Hr003 Remote Branch Retention

## Implemented scope

- Removed `kis_github_delete_registered_branch` from the registered GitHub capability descriptor and input-schema surface.
- Safe PR closeout now refreshes default-branch tracking and retains the remote review branch instead of deleting it.
- Registered-operation dispatch fails closed with `UNKNOWN_REGISTERED_GITHUB_OPERATION` for the removed operation.
- `RegisteredGitHubOperations.delete_remote_branch` remains only as a no-side-effect compatibility rejection with `REMOTE_BRANCH_DELETE_PROHIBITED`.
- `docs/TRUST-MODEL.md` now states that a retained commit SHA is not quarantine of a remote ref and normal Work retains review branches.

## Validation evidence

- RED: 5 focused failures on the prior destructive capability/workflow contract.
- GREEN: 128 focused capability/workflow tests passed after implementation and compatibility hardening.
- `pwsh -NoProfile -File scripts/change-workflow.ps1 check`: passed with all changed paths inside Change 218 scope.
- `git diff --check`: passed.
- `pwsh -NoProfile -File scripts/verify.ps1`: passed; full pytest reached 100% with only existing warnings/skips and all repository verification checks green.

## Review

- Code-quality review: clean; reported only intentional removals.
- Safety/security review: Codex reviewer clean after the first NVIDIA route returned malformed reviewer output rather than findings.
- API-contract review: initial compatibility concern resolved by the no-side-effect legacy method; rerun clean with both dispatcher and direct-call error contracts pinned.
- Test-quality review: clean.

## Hard-rule audit and residual ownership

- Live capability audit found `github_delete_file` and `supabase_delete_branch` still eligible through generic external dispatch with no capability-layer HR-003 guard.
- Follow-up defect #432 owns the cross-provider irreversible-delete boundary; Change 218 does not silently broaden into that remediation.
- The normal registered-branch/PR-closeout violation identified by #431 is fully addressed by this change.

## Git and merge

- Branch: `change/218-hr003-remote-branch-retention`
- Worktree: `.work/worktrees/218-hr003-remote-branch-retention`
- Commit/PR/merge evidence is recorded by the governed publication and Work Management lifecycle after this file is committed.
