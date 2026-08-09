# GitHub Project Write Commissioning Implementation Plan

> **For agentic workers:** Execute this plan task-by-task in the governed 085 worktree. Use test-first implementation for behavior changes.

**Goal:** Commission supervised GitHub Project writes for `kis-mcp` Project #1 and enable reconciliation with all automation disabled.

**Architecture:** Reuse the existing central registry, Work Management service, workflow tool, and bounded GitHub Project adapter. Add no production subsystem; the repository change is one configuration promotion plus focused regression/evidence documentation after live commissioning proves the existing path.

**Tech Stack:** Existing Python/pytest configuration loaders, current KIS GitHub MCP runtime, GitHub Project #1, governed PowerShell/Git workflow.

## Global constraints

- Stay inside `scope.json`; do not edit 083/084-owned paths.
- Preserve exactly HR-001 / HR-002 / HR-003.
- No new GitHub client, GraphQL surface, delete/archive operation, provider/auth change, or automation enablement.
- Use `C:\Projects\.kis-mcp\python-env\Scripts\python.exe -m pytest` for focused tests.

### Task 1: RED commissioning configuration test

**Requirements:** R1, R5, R6, R7

**Files:**
- Create: `tests/project_onboarding/test_github_project_commissioning.py`

- [ ] Add a focused test that loads the checked-in registry and Work Management settings and requires Project #1, `reconciliation=enabled`, the other feature modes unchanged, and every automation flag false.
- [ ] Run the focused test and confirm it fails only because reconciliation is still `read_only`.

### Task 2: Establish PR and live commissioning evidence

**Requirements:** R2, R3, R4

**Files:**
- Update: `.work/changes/085-github-project-onboarding-commissioning/closeout.md`

- [ ] Commit the RED test/spec/plan state and push 085.
- [ ] Create the 085 pull request against `main` without merging it.
- [ ] Re-read Project #1 inventory and record its exact before-state.
- [ ] Exercise the existing bounded write path with the 085 PR: add once and set `Status=In Progress`.
- [ ] Replay the same source/idempotency operation and prove there is still exactly one matching PR item.
- [ ] Exercise stale-revision protection and prove conflict/no overwrite.
- [ ] Record bounded live evidence; do not store credentials or opaque secrets.

### Task 3: GREEN configuration promotion

**Requirements:** R5, R6, R7

**Files:**
- Modify: `settings/work-management/github-projects.settings.json`
- Update: `tests/project_onboarding/test_github_project_commissioning.py`

- [ ] Change only `features.reconciliation` from `read_only` to `enabled`.
- [ ] Run the focused test and confirm it passes.
- [ ] Confirm all automation values remain false and no unrelated JSON changes occurred.

### Task 4: Documentation, review, and verification

**Requirements:** R2-R7

**Files:**
- Create: `docs/development/github-project-onboarding/commissioning.md`
- Update: `.work/changes/085-github-project-onboarding-commissioning/closeout.md`

- [ ] Document the exact commissioned Project identity, supported manual flow, safety controls, and automation-off state.
- [ ] Run `pwsh -NoProfile -File scripts/change-workflow.ps1 check`.
- [ ] Run focused tests with the locked Python interpreter.
- [ ] Request final code review and resolve blocking findings.
- [ ] Run `pwsh -NoProfile -File scripts/verify.ps1`; record any unrelated pre-existing failure explicitly.
- [ ] Commit and push the final exact head, then wait for required PR checks.

### Task 5: Land and close commissioning

**Requirements:** R3, R8 acceptance

- [ ] Merge only after exact-head checks and review are acceptable.
- [ ] On the post-merge runtime, set the tracked PR item to `Done` through the commissioned reconciliation path.
- [ ] Re-read inventory and confirm exactly one matching 085 PR item with `Status=Done`.
- [ ] Complete closeout evidence and run governed worktree cleanup from clean `main`.
