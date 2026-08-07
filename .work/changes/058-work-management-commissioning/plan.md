# Work Management Commissioning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Commission P5 against `NielPieterse0` user Project `#1` while making the enabled runtime genuinely read-only.

**Architecture:** Keep GitHub response-shape handling inside `providers/github/projects/adapter.py`, keep feature-mode enforcement inside the provider-neutral `WorkManagementService`, and change only strict JSON configuration plus programme/change evidence. Do not touch provider authentication/routing or the three-rule policy.

**Tech Stack:** Python 3.11+, FastMCP 3.4.4, pytest 8.x, strict JSON settings, PowerShell repository workflow, official GitHub MCP `v1.8.0`.

## Global constraints

- Stay inside `scope.json`; `settings/providers/github-mcp.provider.json` and `policy/**` are excluded.
- Use test-first red/green evidence for both behavior fixes.
- Do not call `projects_write` or any Project mutation during commissioning.
- All work-management automation flags remain `false`.
- Final remote mutation remains disabled by feature mode; numeric write-side item-ID adaptation is deferred.

---

### Task 1: Normalize the observed GitHub Project read contract

**Requirements:** R2, R4

**Files:**
- Modify: `tests/providers/github/projects/test_adapter.py`
- Modify: `src/kis_mcp/providers/github/projects/adapter.py`

**Interfaces:**
- Consumes: `GitHubProjectInventoryAdapter.read_inventory(ProjectBinding, field_names=(), item_limit=100)`.
- Produces: provider-neutral `ProjectInventory` with string stable identities and scalar option names.

- [ ] Add a regression test using the live `v1.8.0` shapes: numeric `id`, string `node_id`, `data_type="single_select"`, and option `name={"html":"Todo","raw":"Todo"}`.
- [ ] Run only that test and confirm it fails because current normalization requires string `id`/`name`.
- [ ] Add minimal adapter helpers that prefer non-empty `node_id`, otherwise stringify a scalar `id`, and extract structured text from `raw`/`html` only where the provider emits it.
- [ ] Rerun the focused adapter tests and confirm green.

---

### Task 2: Enforce configured read-only feature modes

**Requirements:** R3, R4

**Files:**
- Modify: `tests/work_management/test_service.py`
- Modify: `src/kis_mcp/work_management/service.py`

**Interfaces:**
- Consumes: `WorkManagementSettings.feature_mode(name)` and existing `WorkManagementService.reconcile()` / `persist_review_artifact()`.
- Produces: preview-only reconciliation when mode is `read_only`; mutation attempts raise before backend/store side effects.

- [ ] Add a test with `reconciliation=read_only` proving preview succeeds but `apply=true` raises and leaves `Backend.applied` empty.
- [ ] Add a test with `review_import=read_only` proving persistence raises before the evidence-store factory is called.
- [ ] Run those tests and confirm both fail against current behavior.
- [ ] Add one small service-level feature guard: `disabled` rejects use, `read_only` permits reads/previews but rejects mutation, and `enabled` permits the existing mutation path.
- [ ] Rerun `tests/work_management/test_service.py` and confirm green.

---

### Task 3: Bind and enable the read-only commissioned Project

**Requirements:** R1, R3, R4

**Files:**
- Modify: `settings/work-management/github-projects.settings.json`
- Modify: `tests/work_management/test_settings.py`

**Interfaces:**
- Produces checked-in settings with `enabled=true`, `project_number=1`, existing read-only feature modes, and all automation flags false.

- [ ] Update the checked-in settings test to require `enabled is True`, Project number `1`, reconciliation/review-import `READ_ONLY`, and `not any(dict(settings.automation).values())`.
- [ ] Run that test and confirm it fails against the current disabled/null binding.
- [ ] Set `enabled` to `true` and `project_number` to `1`; do not change feature, automation, gate, or evidence values.
- [ ] Validate JSON and rerun settings tests.

---

### Task 4: Reconcile commissioning documentation and run verification

**Requirements:** R5, R6

**Files:**
- Modify: `.work/programmes/work-management/target-spec.md`
- Modify: `.work/changes/058-work-management-commissioning/tasks.md`
- Modify: `.work/changes/058-work-management-commissioning/closeout.md`

- [ ] Record the live pre-bind evidence: Project `#1`, title `KIS Work Management`, private, Status options `Todo/In Progress/Done`, zero items, complete pagination, and authenticated runtime.
- [ ] Update the programme commissioning state without claiming post-merge `kis-op` inventory until it is actually run.
- [ ] Run focused adapter/service/settings tests.
- [ ] Run `pwsh -NoProfile -File scripts/change-workflow.ps1 check` from the 058 worktree.
- [ ] Run `pwsh -NoProfile -File scripts/verify.ps1` from the 058 worktree.
- [ ] Review the final diff against R1-R6, including absence of Project write calls and provider/policy changes.
- [ ] Commit, push, create the PR, and take it to verified readiness under PR Completion.
- [ ] After explicit landing approval and merge, restart/authenticate `kis-op` once and run `project_management_inventory(project_id="kis-mcp", field_names=["Status"])`; only then mark live P5 commissioning complete and clean up change 058.

## Self-review

- R1 maps to Task 3 and the pre/post-merge live checks in Task 4.
- R2 maps to Task 1 regression evidence.
- R3 maps to Task 2 service guards plus Task 3 retained feature modes.
- R4 maps to Tasks 1-3 and final diff review.
- R5 maps to Task 4 focused, scope, repository, and live verification.
- R6 maps to Task 4 programme/closeout reconciliation.
- No placeholder implementation steps remain; deferred write-side numeric item-ID adaptation is explicitly out of scope in the specification.
