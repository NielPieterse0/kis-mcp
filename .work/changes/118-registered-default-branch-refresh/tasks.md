# Tasks: Registered Default Branch Refresh

- [x] Confirm GitHub MCP expected-SHA authority and registered-repository scope.
- [x] Implement bounded default-branch tracking refresh with approval, exact verification, controlled materialization, and CAS ref update.
- [x] Integrate refresh before governed worktree creation and immediately after every composed registered-PR merge workflow.
- [x] Run scope check, Ruff, focused regression tests, and direct Git missing-object behavior check.
- [x] Run canonical `scripts/verify.ps1 -SkipDependencySync`; full repository verification passed.
- [x] Attempt both configured independent reviewers and retain backend-failure diagnostics; inspect the bounded diff directly.
- [ ] Execute exact PR merge, post-merge refresh commissioning, review-branch deletion, and worktree cleanup; retain final evidence on Work Management issue #159 while leaving it non-final.
