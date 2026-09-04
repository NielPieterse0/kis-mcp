# Change: Closed Orphan Worktree Reconciliation

- **Change ID**: `643-closed-orphan-worktree-reconciliation`
- **Risk Profile**: lean

## Outcome

Safely reconcile terminal unclaimed orphan worktrees while preserving unmerged branch and evidence.

## Scope and acceptance

- Add a first-class `retire_closed_orphan_worktree` capability and CLI path.
- Require explicit terminal-work confirmation, no current claim, and a clean exact worktree.
- Preserve the `change/<id>` branch and committed evidence even when it is unmerged.
- Keep normal validation and merged-worktree cleanup fail-closed and unchanged.
- Surface orphan topology diagnostically without widening execution authority.

## Implementation and verification

- Implementation notes: retirement removes only the worktree registration/path; it never deletes the branch. Removal remnants are recoverably moved beneath `.backup` if Git unregisters the worktree but leaves files behind.
- Focused checks: `tests/test_change_governance.py`, `tests/capabilities/test_governed_change.py`, and `tests/capabilities/test_exposure_execution.py` pass; change scope check passes.
- Review findings: initial proposal to ignore all unclaimed worktrees was rejected during safety review and reverted. Strict validation remains in force. Re-review has no findings.
- Live recovery evidence: commodity issue #78 was re-read as closed/completed, Done, Verification Passed, no Execution Owner; `change/078-diagnostics-agent3` was clean and retired with its branch preserved.
- Residual risk: terminal-work confirmation is explicit caller evidence at this supervised recovery boundary; retirement still refuses any live claim or dirty worktree.
- Closeout state: ready for commit and exact-head CI.
