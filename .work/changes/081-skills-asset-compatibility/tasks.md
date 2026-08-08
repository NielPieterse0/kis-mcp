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
- [ ] Stage and commit only declared owned paths.
- [ ] Push `change/081-skills-asset-compatibility` and open/update its PR.
- [ ] Obtain exact-head Work Management evidence and resolve review blockers.
- [ ] Land only the verified exact head through the approved PR landing path.
- [ ] Record merge/verification evidence, close change metadata, and run governed cleanup from clean `main`.
- [ ] Re-run canonical `main` verification and confirm only primary `main` plus preserved clean 040 remain.
