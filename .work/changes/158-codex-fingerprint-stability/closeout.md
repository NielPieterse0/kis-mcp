# Closeout: Codex Fingerprint Stability

## Implemented scope

- Root-caused #261 to PowerShell native stderr capture: Git line-ending warnings merged with `2>&1` became complex `ErrorRecord` values and destabilized JSON fingerprint serialization.
- Fingerprinting now hashes successful Git stdout/state only while preserving existing non-zero Git exit checks and state dimensions.
- Added regression coverage proving a pre-existing dirty diff with a Git warning survives a no-op Codex invocation.
- Preserved the existing deliberate-mutation regression and exit-code-86 fail-closed behavior.

## Validation evidence

- Red evidence: new dirty-diff regression failed on the original wrapper with exit 86 and JSON-depth warnings while repository status/diff remained unchanged.
- Focused checks: 14/14 Codex adapter/wrapper tests passed after the fix.
- Affected checks: 70/70 Codex adapter plus code-review workflow tests passed.
- `git diff --check`: passed.
- Scope check: passed; only declared wrapper, test, and change-record paths changed.
- Verification selection: repository verifier and Python test handoffs identified; execution is reserved/unavailable locally, so exact-head PR CI remains the canonical full gate.
- Ruff: not present in the current locked environment; no alternate environment was substituted.

## Review

- Required code-quality review: NVIDIA Super completed with complete evidence and zero findings.
- Review confirmed stderr diagnostics are excluded without weakening exit-code checks or the mutation comparison.

## Git and merge

- Branch: `change/158-codex-fingerprint-stability`
- Worktree: `.work/worktrees/158-codex-fingerprint-stability`
- Commit: pending.
- Pull request / exact-head CI / merge: pending.
- Cleanup: pending merge.

## Recovery

Revert the bounded wrapper/test commit. No persistent state, migration, or runtime configuration changes are involved.

## Residual items

- The pre-existing pytest package import-order circularity remains outside #261; focused verification pre-imported `kis_mcp.workflows` to exercise the affected tests.
- The KIS registered-default refresh operation failed before change creation because its Git transport could not resolve HTTPS credentials; GitHub provider truth and local `main` independently matched exact SHA `4e107b660a9925569d32eb19927b361da7149de5`.
- Unrelated #265, #273, #274, #270, and #241 work remains outside this lane.
