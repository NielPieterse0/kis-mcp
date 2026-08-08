# Workflow Discovery Bridge Implementation Plan

> **For agentic workers:** Execute this plan task-by-task and keep the declared scope current.

**Goal:** Deliver approved Slice B then Slice A in two reviewable PR batches from one isolated worktree.

**Architecture:** Keep Discover planning and Work verification execution separate. `plan_change` composes existing `InspectProjectService` and `AnalyzeChangeService` evidence plus bounded `.work/changes/*/scope.json` claim reads. `run_verification` re-discovers a stable declaration and maps its fixed profile/arguments to an existing process tool call with middleware enabled. After change 063 released its claims, the final adapter preserves declared executable steps in shared `WorkflowDescriptor` metadata, resolves them against the live augmented catalogue, and delegates recommendation scoring to the existing deterministic weighted matcher.

**Tech Stack:** Python 3.13 project runtime, FastMCP 3.4.4, pytest, PowerShell repository verification, Git/GitHub provider for delivery.

## Global constraints

- Preserve exactly HR-001, HR-002, HR-003 and all original provider middleware/schema validation.
- No arbitrary command field in verification APIs; no network from Work; Discover remains read-only.
- Use TDD for every behavior change and keep generated state under `C:\Projects\.kis-mcp`.
- Do not edit another active change's exclusive paths; update scope before any newly claimed path.

---

### Task 1: Slice B — bounded `plan_change` preparation

**Requirements:** REQ-001, REQ-005
**Files:** create `discover/planning_contracts.py`, `discover/planning.py`, tests; modify only owned Discover registration files.

- [ ] Write contract/service/tool tests for deterministic authority, affected tests/verifications, active claims, conflicts, unknowns, bounds, and no execution.
- [ ] Run focused tests and confirm RED because `plan_change` does not exist.
- [ ] Implement contracts and service by composing existing Discover services; parse only bounded local claim JSON.
- [ ] Register the read-only tool/contribution and rerun focused Discover tests to GREEN.
- [ ] Run scope check, review, canonical verification, commit, create PR, obtain exact-head evidence, merge, and reconcile the same worktree for Batch 2.

### Task 2: Slice A — `run_verification` execution bridge

**Requirements:** REQ-002, REQ-005
**Files:** create `workflows/verification/**`, tests; modify owned gateway registration.

- [ ] Write tests proving stable-ID lookup, unknown-ID rejection before execution, fixed profile mapping, middleware-backed process invocation, bounded result evidence, pass/fail/timeout classification.
- [ ] Run focused tests and confirm RED because the Work bridge does not exist.
- [ ] Implement the verification contract/discovery lookup/command identity and executor; register `run_verification` without arbitrary shell input.
- [ ] Rerun focused tests to GREEN and verify no direct-profile or policy widening.

### Task 3: Workflow integrity and recommendation hardening

**Requirements:** REQ-003, REQ-004
**Files:** after 063 release: exact central workflow/capability descriptor and resolver paths plus focused verification-workflow tests.

- [x] Revalidate active claims; expand `scope.json` only for now-free exact paths.
- [x] Write RED tests for executable-step metadata, unresolved executable-step ineligibility, shared `verify-current-change`/`triage-exact-head-ci`, and richer deterministic matching.
- [x] Implement minimum compatible step metadata/resolution and shared workflow descriptors; preserve legacy procedure-only symbolic steps with empty executable-step metadata.
- [x] Confirm realistic verification and CI-triage prompts recommend the intended workflows and unresolved executable steps cannot be eligible.

### Task 4: Batch 2 review, verification, delivery, closeout

**Requirements:** REQ-001–REQ-005

- [ ] Run focused suites, change-workflow check, advisory review, and `scripts/verify.ps1` on the exact local head.
- [ ] Create the second PR, verify exact-head CI, resolve findings without suppressing checks, and merge safely.
- [ ] Reconcile local main, update documentation/closeout with exact evidence, run final verification, and clean 079 only after merge eligibility is proven.
