# Skill Capability Refresh Implementation Plan

> **For agentic workers:** Execute task-by-task and keep the declared scope current.

**Goal:** Keep skill-derived capability discovery synchronized with the active Skills snapshot after refresh, without a gateway rebuild.

**Architecture:** Extend `CapabilityRuntimeState` with an optional live contribution source. Gateway composition keeps non-skill contributions static and supplies a callback that rebuilds only skill contributions from the current `SkillsService` snapshot. Existing runtime-tool augmentation remains layered on top.

**Tech Stack:** Python 3.13, FastMCP runtime composition, pytest, KIS change governance.

## Global constraints

- Stay inside `scope.json`.
- Add tests before behavior changes.
- Do not touch change 140-owned capability surface/execution paths.
- Preserve current immutable Skills snapshot and fail-closed refresh semantics.
- Do not add a second capability registry or persistent cache.

---

### Task 1: Prove dynamic contribution refresh at the runtime boundary

**Files:**
- Modify: `tests/capabilities/test_runtime_refresh.py`
- Modify: `src/kis_mcp/capabilities/runtime.py`

- [ ] Add a failing test showing a runtime object still exposes its startup contribution after the source changes.
- [ ] Add the smallest optional contribution-source contract to `CapabilityRuntimeState`.
- [ ] Prove subsequent catalogue/readiness/resolver reads use the refreshed contribution set.

### Task 2: Bind skill contributions to the active Skills snapshot

**Files:**
- Modify: `src/kis_mcp/skills/platform.py`
- Modify: `src/kis_mcp/gateway/composition.py`
- Modify: `tests/skills/test_dynamic_catalogue_startup.py`

- [ ] Add a failing refresh regression covering removed and newly available classified skills.
- [ ] Add a bounded helper that derives capability contributions from the current `SkillsService` snapshot.
- [ ] Make gateway capability composition use the helper as the dynamic contribution source while keeping non-skill contributions static.
- [ ] Preserve unclassified-skill behavior.

### Task 3: Review, verify, and prepare delivery

- [ ] Run focused capability/Skills tests.
- [ ] Run `pwsh -File scripts/change-workflow.ps1 check 142-skill-capability-refresh`.
- [ ] Run affected verification through KIS and inspect the exact working-tree diff.
- [ ] Run independent code review; fix blocking findings and rerun checks.
- [ ] Commit the exact verified change and prepare the governed pull request.
- [ ] Require exact-head GitHub Actions evidence before landing.
- [ ] Reconcile issue/Project state and cleanup after merge.
