# PromotionReady-to-Done Convergence Implementation Plan

> **For agentic workers:** Execute this plan task-by-task under repository/KIS authority. Use TDD for behavior changes; do not create a parallel workflow or Git authority.

**Goal:** Turn the existing persisted PromotionReady handoff and PromotionController into the production, resumable, agentless Work-to-Done MCP convergence path for #585.

**Architecture:** Keep `PromotionController` as the durable ordered state machine. Extend its invoker contract so later stages receive the persisted observations of completed stages, then add a focused production promotion service/invoker that composes existing registered GitHub and Work operations rather than reimplementing them. Register one optional MCP Task tool with structured synchronous fallback; keep KIS checkpoints authoritative across task/session loss.

**Tech Stack:** Python 3.13, FastMCP 4, `fastmcp_tasks`, existing KIS capability dispatch, Work Management, registered GitHub operations, pytest/uv.

**Spec:** `.work/changes/263-promotion-ready-to-done/spec.md`

## Global constraints

- Stay inside `scope.json` and existing HR-001/HR-002/HR-003 authority.
- Use current registered GitHub/Work operations; no raw parallel GitHub mutation implementation.
- No substantive KIS review after PromotionReady.
- Exact-head Actions and Work merge readiness remain mandatory.
- Durable KIS checkpoint state is authoritative; MCP task IDs are not.
- Add failing tests before each production behavior change.
- Update `SPEC.md` only after implementation evidence proves the new current behavior.

---

### Task 1: Make PromotionController observations usable by later stages

**Files:**
- Modify: `tests/workflows/once_through/test_once_through.py`
- Modify: `src/kis_mcp/workflows/once_through/controller.py`

**Interfaces:**
- Consumes: `PromotionController.converge(operation_id, promotion_handoff)` and persisted `observations`.
- Produces: `PromotionInvoker(stage, promotion_handoff, observations)` semantics with immutable prior-stage observation input.

- [ ] Add a test proving stage N+1 receives stage N's persisted exact observation and resumed stages receive the saved prefix.
- [ ] Run that test and confirm it fails because the current invoker receives only the handoff.
- [ ] Extend the controller invoker contract minimally and keep checkpoint validation/fingerprinting unchanged.
- [ ] Run once-through controller tests and confirm no replay regression.

### Task 2: Build the production registered-operation promotion invoker

**Files:**
- Create: `src/kis_mcp/workflows/once_through/promotion.py`
- Test: `tests/workflows/once_through/test_promotion_runtime.py`

**Interfaces:**
- Consumes: persisted PromotionReady handoff, prior controller observations, KIS nested structured-operation invoker.
- Produces: `PromotionStageService.invoke(stage, handoff, observations) -> dict[str, Any]` with `passed|satisfied|applied` or precise resumable blocked result.

- [ ] Write tests for each canonical stage and exact data dependency between refresh/reconcile/PR/CI/readiness/merge/landed/docs/Done/cleanup.
- [ ] Prove tests fail before the service exists.
- [ ] Implement the smallest stage adapter by composing existing registered GitHub and Work operations.
- [ ] Add tests proving pending CI and false merge readiness stop before merge, and existing exact applied state is reused.
- [ ] Add a test proving no implementation verification/review operation is ever invoked by the promotion service.

### Task 3: Register durable `converge_change_to_done`

**Files:**
- Modify: `src/kis_mcp/workflows/once_through/tools.py`
- Modify: `src/kis_mcp/workflows/platform.py`
- Modify: `tests/discover/test_tool_registration.py`
- Test: `tests/workflows/once_through/test_promotion_runtime.py`

**Interfaces:**
- Consumes: `TaskHandoffStore.load_promotion(work_id)`, `PromotionStateStore`, `PromotionController`, production stage service.
- Produces: public `converge_change_to_done(work_id: str, approved: bool = ...)` optional MCP Task result with stable KIS operation identity.

- [ ] Add registration/task-config tests before implementation.
- [ ] Confirm the public tool is absent/failing.
- [ ] Register the tool with `LONG_RUNNING_TASK_CONFIG`, structured output, and explicit mutation approval semantics compatible with current external-operation rules.
- [ ] Persist/reuse one deterministic promotion operation ID derived from the immutable handoff identity.
- [ ] Test completed resume is a no-op and blocked resume continues from the exact checkpoint.

### Task 4: Document and verify current behavior

**Files:**
- Modify: `SPEC.md`
- Modify: `.work/changes/263-promotion-ready-to-done/tasks.md`
- Modify: `.work/changes/263-promotion-ready-to-done/closeout.md`

- [ ] Update `SPEC.md` narrowly to list `converge_change_to_done` as an optional MCP Task and describe durable KIS checkpoint authority.
- [ ] Run focused once-through and registration tests under the repo-locked `uv` environment.
- [ ] Run `pwsh -File scripts/change-workflow.ps1 check` from the change worktree.
- [ ] Execute the governed implementation verification/review once and resolve any material findings before PromotionReady.
- [ ] Record exact evidence and proceed through governed publication, exact-head Actions, merge readiness, merge, documentation reconciliation, Work completion, and cleanup.
