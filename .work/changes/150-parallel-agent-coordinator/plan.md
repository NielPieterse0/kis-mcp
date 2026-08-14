# Parallel Agent Coordinator Slice 2 Implementation Plan

> Execute #248 inside the existing `150-parallel-agent-coordinator` worktree. Do not create another coordinator worktree and do not begin #249.

**Goal:** Make reservation admission atomic so conflicting agents cannot both acquire mutation authority, while preserving liveness for disjoint work.

**Architecture:** Keep the Slice 1 schemas authoritative. Add one internal coordinator reservation service that serializes the admission transaction with an OS-level mutex, persists append-only admission evidence, validates global claims, delegates governed branch/worktree creation to the existing change workflow, and couples configured Work Management claims through injected adapters.

**Development level:** Complex. The change crosses repository-governance and public-contract boundaries, introduces durable state, and coordinates multiple authorities. Parent scope and sequencing are already approved, so this slice does not redesign the architecture.

## Constraints

- Stay inside the parent coordinator-owned paths.
- Preserve HR-001 / HR-002 / HR-003 exactly; do not add policy rules.
- Registry/runtime connectivity never grants mutation authority.
- `authority_revision=1` and `fence_token=1` are issuance evidence only; active fencing/expiry/recovery belongs to #249.
- Do not implement planner/work-packet production (#250), worker execution (#251), reconciliation/integration (#252), or telemetry/commissioning (#253).
- Do not push, open a PR, merge, clean up, or restart runtimes as part of this slice.

### Task 1: Reservation race contract

**Files:**
- Create/modify `tests/workflows/coordinator/test_reservation_service.py`
- Modify `tests/workflows/coordinator/test_contract_catalog.py`

- [x] Add RED tests for conflicting concurrent reservations, disjoint concurrent reservations, sequence uniqueness, shared-path coordination, duplicate outcome rejection, exact base identity, Work claim coupling, and boundary enforcement.
- [x] Confirm RED because the Slice 2 runtime coordinator package did not exist.

### Task 2: Atomic admission service

**Files:**
- Create `src/kis_mcp/workflows/coordinator/models.py`
- Create `src/kis_mcp/workflows/coordinator/service.py`
- Create `src/kis_mcp/workflows/coordinator/__init__.py`

- [x] Implement validated reservation request/result models.
- [x] Serialize admission with a cross-process file mutex.
- [x] Allocate the next sequence from active claims, historical change records, and consumed journal evidence.
- [x] Validate duplicate identities, exclusive overlaps, and shared-path coordination before governed creation.
- [x] Persist append-only pending/reserved/aborted/degraded admission events under the declared boundary.
- [x] Issue initial reservation/lease/fence identity without implementing #249 enforcement.

### Task 3: Existing-authority adapters

**Files:**
- Create `src/kis_mcp/workflows/coordinator/adapters.py`

- [x] Add a local adapter for authoritative change listing, exact Git base resolution, and existing governed `change-workflow.ps1 new` creation.
- [x] Pass configured Work Management metadata into the injected claim adapter and require compensation support.
- [x] Re-read the governed claim after creation and reject identity mismatch.
- [x] Keep the coordinator service internal; do not register an MCP tool or alternate mutation authority in Slice 2.

### Task 4: Documentation, review, verification, and handoff

- [x] Update the coordinator module product spec with Slice 2 implementation status and remaining slice boundaries.
- [x] Run the full coordinator suite and relevant governance/unit checks.
- [x] Run Python compilation and `git diff --check`.
- [x] Run the governed scope check.
- [x] Perform required `code-quality`, `architecture`, and `api-contracts` reviews; fix/adjudicate findings and rerun affected evidence.
- [ ] Commit Slice 2 on the existing parent branch and leave the parent governed change active for #249.
