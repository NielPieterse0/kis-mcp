# Tasks: Dual Instance Commissioning

- [x] Confirm authority, approved design, development level, and non-overlapping scope.
- [x] Create governed worktree from clean `main` and pass baseline verification.
- [x] Add failing tests for `kis-op`/`kis-dev` names, aliases, exact ports, and invalid mappings.
- [x] Implement configuration-driven app identity and centralized selector normalization.
- [x] Add failing tests for concurrent startup, own-port exclusivity, and startup identity evidence.
- [x] Remove peer-instance rejection while retaining selected-port hardening.
- [x] Align `SPEC.md` and `docs/OPERATIONS.md` with concurrent `kis-op`/`kis-dev` operation.
- [x] Run focused tests and `pwsh -NoProfile -File scripts/change-workflow.ps1 check`.
- [x] Run `pwsh -NoProfile -File scripts/verify.ps1`.
- [ ] Complete the operator-unlocked live `kis-dev` tunnel smoke while the existing `kis-op` remains healthy; automated preflight confirmed `kis-op` on `8010` and `8011` free, but this execution context could not present the vault prompt.
- [x] Review the complete diff and record closeout evidence.
- [x] Commit the implementation, push the branch, and create PR #50.
- [ ] Shepherd the final exact head through PR Completion to verified readiness.
- [ ] Obtain explicit exact-head merge approval, land through PR Completion, and clean the worktree/branches.
