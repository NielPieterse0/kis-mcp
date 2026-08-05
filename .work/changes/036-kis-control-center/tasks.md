# KIS Control Center Tasks

- [x] Read repository authority and approved design.
- [x] Classify development level as Medium.
- [x] Create isolated worktree and bounded scope.
- [x] Write approved specification and implementation plan.
- [x] Task 1: settings and snapshot contracts.
- [x] Task 2: bounded local snapshot collection.
- [x] Task 3: self-contained MCP App renderer and server.
- [x] Task 4: documentation, review, focused verification, change-workflow check, whitespace validation, and full repository verification.
- [ ] Integration lifecycle: commit, push, pull request, exact-head review, merge, and worktree/branch cleanup.

## Verification evidence

- Focused Control Center suite: 13 passed.
- `scripts/change-workflow.ps1 check`: passed and reported only declared paths.
- `git diff --check`: passed.
- `scripts/verify.ps1`: passed after renaming test modules to globally unique basenames; all repository tests completed with the existing two skips.
- JSON validation: `settings/control-center.settings.json` and `contracts/control-center/settings.schema.json` passed.

## Governance history

Initial registration through `change-workflow.ps1 new` was blocked by a then-active exclusive overlap between changes `029-tools-code-tooling` and `035-llm-capability`. This change was created under the documented emergency exception with disjoint ownership. Final change-workflow and repository governance checks pass with 29 claims and no overlap involving change `036-kis-control-center`.
