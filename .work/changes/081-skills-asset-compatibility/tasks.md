# Tasks: Skills Asset Compatibility

- [x] Confirm authority, Medium development level, and exact owned scope.
- [x] Reproduce the packaged-skill compatibility failures from primary `main` evidence.
- [x] Add bounded JSON/schema/config support for observed assets and exact `LICENSE`.
- [x] Add explicit capability metadata for the 12 newly installed shared Skills.
- [x] Add/update regression coverage for Skills and capability composition.
- [x] Re-review the final diff against `spec.md` and `plan.md`; fix the extensionless replacement consistency defect found during review.
- [x] Run `pwsh -NoProfile -File scripts/change-workflow.ps1 check` on the final pre-commit state.
- [x] Run focused Skills/capability/Gateway verification on the final implementation state (28 passed).
- [x] Run `pwsh -NoProfile -File scripts/verify.ps1` on the final pre-commit state.
- [x] Stage and commit only declared owned paths (`30df06a7b8da42dd8adb13dbc5e6950f69321170`).
- [x] Push `change/081-skills-asset-compatibility` and open PR #100.
- [x] Obtain exact-head Work Management evidence; `Validate P5 at exact revision` passed on the authorized head.
- [x] Land only the verified exact head through the approved PR landing path; merge commit `c1352fadf736dca0724468b6e67aed8f85e7d624`.
- [x] Record implementation merge/verification evidence and close the 081 change metadata.
- [x] Prepare the closeout-only record so governed cleanup and canonical `main` verification can run after it lands.
