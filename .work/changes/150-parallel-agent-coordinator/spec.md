# Change Specification: Parallel Agent Coordinator

- **Change ID**: `150-parallel-agent-coordinator`
- **Status**: Active — Slice 2 (#248)
- **Complexity**: `large`
- **Risk triggers**: `architecture_boundary`, `public_contract`

## Outcome

Build the KIS-native coordinator as one governed #241 change. Slice 1 (#247) established architecture and contracts; Slice 2 (#248) implements atomic reservation, globally unique human-facing sequence allocation, and global path-claim admission without entering Slice 3 lease/recovery behavior.

## Authority and scope

- Authoritative sources: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, #241, #247, and #248.
- Owned paths remain coordinator-specific: contracts, coordinator runtime package/tests, coordinator module spec, and this change record.
- Current Skills telemetry, review-backend, GitHub Project adapter, policy, root `SPEC.md`, and `docs/OPERATIONS.md` remain outside this slice.
- Slice sequencing remains strict: `247 -> 248 -> 249 -> 250 -> 251 -> 252 -> 253`.

## Slice 2 requirements

- **REQ-248-01**: Serialize reservation admission so two concurrent candidates cannot both receive conflicting mutation authority.
- **REQ-248-02**: Allocate a globally unique positive numeric sequence and derive a stable governed `NNN-slug` change identity without reusing consumed sequence numbers.
- **REQ-248-03**: Validate duplicate outcome, branch, worktree, exclusive/shared path conflicts, and shared-path coordination before governed creation.
- **REQ-248-04**: Permit overlapping shared claims only with explicit dependency or integration-owner coordination.
- **REQ-248-05**: Capture exact base commit/tree identity before authority issuance.
- **REQ-248-06**: When Work Management metadata is configured, its execution claim MUST be acquired inside the same serialized admission transaction; missing claim/compensation adapters fail closed, and preview/non-Active/unsuccessful mutation evidence is never accepted as a claim.
- **REQ-248-07**: Governed branch/worktree creation MUST use the existing change workflow and the admitted identity; coordinator state does not become an alternate repository authority.
- **REQ-248-08**: Initial authority evidence MUST issue `authority_revision=1`, a unique reservation ID, a unique lease ID, and `fence_token=1`; active lease enforcement remains #249.
- **REQ-248-09**: Admission state MUST be append-only and bounded under the declared project boundary. All coordinator instances for one repository MUST share the same canonical authority state root; consumed sequence numbers are never reused, including after failed or historically closed changes.
- **REQ-248-10**: Runtime/tool discovery remains structurally non-authorizing and Slice 2 exposes no planner, worker, reconciliation, or telemetry service.

## Acceptance

1. Concurrent reservations for the same exclusive path produce exactly one `reserved` result and one deterministic conflict rejection.
2. Concurrent disjoint reservations all succeed and receive distinct change sequences and IDs.
3. Historical closed IDs and consumed journal sequences advance the allocator; no numeric sequence is reused.
4. Shared paths without explicit coordination fail before governed creation; coordinated shared claims are admitted.
5. Duplicate active outcomes/branch/worktree/change identities are rejected before mutation authority is issued.
6. A successful result validates against `coordinator-reservation-v1` and carries exact base plus bounded authority identity suitable for later work-packet production.
7. Configured Work Management metadata is passed intact to the claim adapter together with exact base and reservation identity.
8. Coordinator journal/state writes outside the declared project boundary fail closed.

## Risks and recovery

- The admission mutex deliberately serializes the short reservation transaction. This prioritizes deterministic safety over admission throughput; worker execution remains parallel after admission.
- A crash after a pending journal event can leave a blocking pending reservation. Slice 2 preserves the evidence instead of guessing recovery; #249 owns lease expiry, fencing, reassignment, and recovery transitions.
- If governed creation fails after a Work claim, Slice 2 attempts compensation. Compensation failure records `degraded` state and blocks only intersecting admission until later recovery.
- The current governed change ID format is three numeric digits. Allocation beyond 999 fails explicitly with `CHANGE_SEQUENCE_EXHAUSTED` rather than generating an invalid identity.

## Out of scope

- CAS scope amendment, lease timers/enforcement, expiry, reassignment, and recovery (#249).
- Dependency planning, actual work-packet production, runtime binding resolution, or agent selection (#250).
- Durable worker lifecycle, retry/resume, or MCP worker execution (#251).
- Handoff reconciliation, verification derivation, integration serialization, PR/merge, or cleanup automation (#252).
- Coordinator telemetry, Control Center projection, effectiveness evaluation, operator UX, or commissioning (#253).
