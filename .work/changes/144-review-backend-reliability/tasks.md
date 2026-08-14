# Tasks: Review Backend Reliability

- [x] Confirm authority and scope.
- [x] Implement the approved change.
- [x] Run `pwsh -File scripts/change-workflow.ps1 check`.
- [x] Run focused tests on the reconciled branch head; canonical `scripts/verify.ps1` remains delegated to exact-head PR CI per repository authority.
- [x] Record current review and closeout evidence (both configured live backends failed; manual exact-diff fallback used without claiming automated review success).
- [ ] Merge and run safe cleanup from `main`.
