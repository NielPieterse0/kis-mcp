# Parallel Agent Coordinator Slice 1 Implementation Plan

> **For agentic workers:** Execute this plan task-by-task in the single `150-parallel-agent-coordinator` worktree. Do not create per-slice worktrees.

**Goal:** Deliver #247's authoritative coordinator architecture and executable machine-readable contracts without implementing later-slice orchestration behavior.

**Architecture:** Draft 2020-12 JSON Schemas under `contracts/coordinator/` are the canonical executable Slice-1 contracts. Slice 1 deliberately exposes no runtime coordinator package or loader; later behavioral slices own runtime loading/validation. The long-lived module spec owns target architecture and strict slice sequencing while root `SPEC.md` remains current implementation authority.

**Tech Stack:** JSON Schema Draft 2020-12 and pytest-based contract validation.

## Global constraints

- Stay inside `scope.json`; do not touch active 144/145/148/149 claims.
- Preserve exactly HR-001 / HR-002 / HR-003; coordinator contracts are not a fourth Work rule.
- Registry/discovery and runtime transport never grant mutation authority.
- Worker `done` is not reviewable, delivered, commissioned, or closed.
- Invalid conflict components block only intersecting work; provably disjoint work remains admissible.
- Slice 1 defines contracts only. #248-#253 own behavioral implementation.

---

### Task 1: Contract inventory and state/transport boundaries

**Files:**
- Create: `tests/workflows/coordinator/test_contract_catalog.py`
- Create: `contracts/coordinator/coordinator-state.schema.json`
- Create: `contracts/coordinator/runtime-binding.schema.json`

**Interfaces:**
- The contract directory contains exactly ten stable schema identities; no runtime loader is exposed by Slice 1.
- `runtime-binding` requires resolved runtime/tool identity and fixes `grants_mutation_authority` to `false`.
- `coordinator-state` separates lifecycle states and nests degraded reservation checks under stable component identities.

- [ ] Write inventory tests that require the exact ten schema names, stable `$id` values, strict schemas, and no Slice-1 runtime coordinator package.
- [ ] Run the focused test and confirm it fails before the contract resources exist.
- [ ] Implement the state/runtime schemas as repository-owned contract resources only.
- [ ] Run the focused test and confirm it passes.

### Task 2: Mutation-authority record contracts

**Files:**
- Create: `tests/workflows/coordinator/test_authority_contracts.py`
- Create: `contracts/coordinator/reservation.schema.json`
- Create: `contracts/coordinator/lease.schema.json`
- Create: `contracts/coordinator/scope-revision.schema.json`
- Create: `contracts/coordinator/dependency-dag.schema.json`

**Interfaces:**
- Reservation carries globally unique sequence/change identity, exact base evidence, owned/shared claims, dependency IDs, integration owner, authority revision, lease ID, and fence token.
- Lease carries holder, reservation, monotonically increasing fence token, issued/expiry timestamps, and status.
- Scope revision carries expected/current authority revisions plus explicit claim deltas; later Slice 3 implements CAS.
- Dependency DAG carries nodes/edges and shared-hotspot integration ownership; later Slice 4 implements planning.

- [ ] Write failing schema-validation tests for valid records and invalid missing revision/fence/ownership evidence.
- [ ] Run the focused test and confirm expected failures from missing schemas.
- [ ] Add the four strict schemas with no execution side effects.
- [ ] Run the focused test and confirm it passes.
### Task 3: Work packet, handoff, verification, and reconciliation contracts

**Files:**
- Create: `tests/workflows/coordinator/test_execution_contracts.py`
- Create: `contracts/coordinator/work-packet.schema.json`
- Create: `contracts/coordinator/worker-handoff.schema.json`
- Create: `contracts/coordinator/verification-requirements.schema.json`
- Create: `contracts/coordinator/reconciliation-result.schema.json`
- Create: `contracts/coordinator/examples/degraded-overlap.json`
- Create: `contracts/coordinator/examples/disjoint-admission.json`

**Interfaces:**
- Work packet freezes outcome, bounded scope, acceptance checks, exact base, authority revision/fence, an immutable fingerprinted reference to the canonical runtime binding, and verification requirements.
- Worker handoff records exact head/changed paths/evidence/residual state plus the same immutable runtime-binding ID/fingerprint and may report only worker lifecycle completion.
- Verification requirements carry scope/risk-derived checks and exact-head/provider-native requirements without claiming they passed.
- Reconciliation result carries the runtime-binding ID/fingerprint and an explicit runtime-binding validation alongside fence/scope/global-claim checks; it cannot merge or represent integrated work.

- [ ] Write failing tests for worker-done separation, stale/missing authority evidence, rejected reconciliation violations, and both historical scenarios.
- [ ] Run the focused test and confirm failures are due to missing contracts/examples.
- [ ] Add the four schemas and two bounded examples.
- [ ] Run the focused test and confirm it passes.

### Task 4: Architecture authority and Slice-1 verification

**Files:**
- Create: `docs/COORDINATOR-MODULE-PRODUCT-SPEC.md`
- Modify: `.work/changes/150-parallel-agent-coordinator/{spec.md,plan.md,tasks.md,closeout.md}`

- [ ] Document the four authority planes, state model, contract ownership, degraded-component semantics, planned future ownership map, and `247 -> ... -> 253` sequencing.
- [ ] Explicitly mark runtime services for #248-#253 as not implemented by Slice 1.
- [ ] Run `pwsh -NoProfile -File scripts/change-workflow.ps1 check`.
- [ ] Run `C:\Projects\.kis-mcp\python-env\Scripts\python.exe -m pytest tests/workflows/coordinator -q`.
- [ ] Confirm Slice 1 exposes no runtime coordinator package and all ten schemas pass Draft 2020-12 validation.
- [ ] Perform required `code-quality`, `architecture`, and `api-contracts` reviews on the current Slice-1 diff; fix blocking findings and rerun affected checks.
- [ ] Commit Slice 1 to the existing parent branch and leave the governed change active for #248; do not merge or cleanup the parent change.
