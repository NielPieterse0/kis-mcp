# Tasks: Local Windows Runner

- [x] Confirm repository authority, live issue #338, and related exact-head issue #331.
- [x] Create isolated governed change `179-local-windows-runner` from clean synchronized `main`.
- [x] Record approved scope, architecture, exclusions, and acceptance criteria.
- [x] Add local-runner settings/schema tests and implementation.
- [x] Add Windows Job Object worker tests and implementation.
- [x] Add per-run state, exact detached-worktree materialization, source recheck, and receipt tests/implementation.
- [x] Extend `run_verification` with exact-revision execution and preserve mutable focused verification.
- [x] Propagate exact commit identity through `execute_change_workflow` and fail closed on non-exact evidence.
- [x] Update current product specification and operator verification procedure.
- [x] Run focused execution/verification/change-execution/completion tests.
- [x] Run Windows process-tree containment integration test.
- [x] Run `pwsh -File scripts/change-workflow.ps1 check`.
- [x] Run canonical `pwsh -File scripts/verify.ps1` locally without GitHub Actions.
- [x] Commission two concurrent runs and one registered non-KIS repository.
- [x] Run final required specialist/manual fallback reviews and resolve blocking findings.
- [ ] Publish/reconcile PR, verify exact PR head locally, and retain receipt reference.
- [ ] Merge exact approved head, refresh registered default branch, close issue evidence, and safely clean worktree.
