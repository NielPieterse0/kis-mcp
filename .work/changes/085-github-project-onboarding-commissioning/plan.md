# GitHub Project Write Commissioning Implementation Plan

> **For agentic workers:** Execute task-by-task in governed worktree 085. Use test-first implementation for behavior changes.

**Goal:** Commission supervised GitHub Project writes for `kis-mcp` Project #1 and enable reconciliation with all automation disabled.

**Architecture:** Reuse the existing central registry, Work Management service, workflow tool, and official GitHub MCP Project operations. Fix only live REST-shape compatibility proven by commissioning; add no new subsystem or provider client.

**Tech Stack:** Existing Python/pytest adapters and settings, current authenticated KIS GitHub MCP runtime, Project #1, governed Git/GitHub workflow.

## Global constraints

- Stay inside `scope.json`; do not edit 083/084-owned paths.
- Preserve exactly HR-001 / HR-002 / HR-003.
- No new GitHub client, unrestricted GraphQL, delete/archive, provider/auth change, or automation enablement.
- Keep provider-neutral Project item IDs as strings; live numeric IDs are represented as digit text.
- Use the locked interpreter with `python.exe -m pytest`.

### Task 1: RED commissioning configuration gate

**Requirements:** R1, R7-R9

- [x] Add `tests/project_onboarding/test_github_project_commissioning.py` requiring Project #1, `reconciliation=enabled`, unchanged other feature modes, and all automation false.
- [x] Confirm RED: the test fails only because reconciliation is currently `read_only`.
- [x] Commit and push the RED evidence branch.

### Task 2: TDD live Project item compatibility

**Requirements:** R2-R6, R9

**Files:**
- Modify: `src/kis_mcp/providers/github/projects/adapter.py`
- Modify: `src/kis_mcp/providers/github/project_management.py`
- Create: `tests/project_onboarding/test_live_project_item_compatibility.py`

- [ ] Write failing tests for live REST item normalization: integer `id`, `content_type`, `fields`, `html_url`.
- [ ] Write a failing reconciliation-adapter test proving add response `{id: node-id, item_id: integer}` must drive update with digit-text numeric `item_id`.
- [ ] Run focused tests and confirm the expected failures.
- [ ] Implement the smallest normalization/write-ID changes.
- [ ] Rerun focused tests and confirm green.

### Task 3: Live recheck and configuration promotion

**Requirements:** R2-R8

- [ ] Re-read Project #1 through `project_management_inventory`; confirm issue #102 normalizes as one item with `Status=In Progress`.
- [ ] Exercise the repaired bounded adapter/reconciliation behavior as far as the current read-only runtime permits; record the post-restart apply check for final commissioning.
- [ ] Change only `features.reconciliation` from `read_only` to `enabled`.
- [ ] Run the commissioning configuration test and live-compatibility tests green.
- [ ] Confirm every automation value remains false.

### Task 4: Documentation, review, and exact-head verification

**Requirements:** R2-R9

- [ ] Document Project #1 identity, issue #102 commissioning evidence, supported supervised flow, numeric-ID compatibility, and automation-off state under `docs/development/github-project-onboarding/`.
- [ ] Run governed scope check and focused tests.
- [ ] Request final code review and resolve blocking findings.
- [ ] Run canonical `scripts/verify.ps1`; record unrelated baseline/parallel failures rather than changing their paths.
- [ ] Commit and push the final exact head.
- [ ] Open the 085 PR only when its diff against `origin/main` contains no unrelated local-main commits; wait for exact-head required checks.

### Task 5: Land and final Work Management commissioning

- [ ] Merge only after exact-head checks and review are acceptable.
- [ ] Ensure the running KIS instance has loaded the landed `reconciliation=enabled` setting.
- [ ] Reconcile issue #102 through `project_management_reconcile`, prove replay/no duplicate and stale-revision conflict behavior, then set `Status=Done`.
- [ ] Re-read inventory and confirm exactly one issue #102 item at `Done`.
- [ ] Complete closeout evidence and governed worktree cleanup from clean `main`.
