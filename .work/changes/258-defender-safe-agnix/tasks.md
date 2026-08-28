# Tasks: Defender Safe Agnix

- [x] Confirm #530/#541 authority, operator reactivation, and bounded scope.
- [x] Reproduce Windows Application Control against current 0.45.0 and fresh 0.52.1 Windows binaries.
- [x] Prove Node is the parent, not the blocked component; select KIS-owned WSL2 runtime rather than unrelated Node relocation.
- [x] Add failing tests before implementation.
- [x] Implement authoritative Linux release acquisition, checksum verification, WSL smoke, and recoverable promotion.
- [x] Implement WSL validation invocation and explicit `AGNIX_APPLICATION_CONTROL_BLOCKED` classification.
- [x] Install agnix 0.45.0 and quarantine stale repo-local Windows runtime.
- [x] Run real strict repository workload and capture fresh Code Integrity evidence.
- [x] Reconcile current specification/setup/bootstrap documentation.
- [ ] Prove malformed agent configuration remains strict.
- [ ] Run final focused tests and `scripts/change-workflow.ps1 check`.
- [ ] Complete required review and exact-head GitHub verification.
- [ ] Merge, refresh main, live-prove KIS surface, close Work #530, and clean the governed worktree.
