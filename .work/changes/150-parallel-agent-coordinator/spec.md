# Change Specification: Parallel Agent Coordinator

- **Change ID**: `150-parallel-agent-coordinator`
- **Status**: Active — Slice 3 (#249)
- **Complexity**: `large`
- **Risk triggers**: `architecture_boundary`, `public_contract`

## Outcome

Build the KIS-native coordinator as one governed #241 change. Slice 1 (#247) established architecture/contracts and Slice 2 (#248) implemented atomic reservation admission. Slice 3 (#249) adds revision-safe scope mutation, lease/heartbeat enforcement, monotonic fencing, expiry/reassignment, deterministic restart recovery, and degraded-component liveness without entering Slice 4 planning/work-packet behavior.

## Authority and scope

- Authoritative sources: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, #241, #247, #248, and #249.
- Owned implementation paths remain the parent coordinator contracts/runtime/tests/module spec/change record.
- The governed `.work/changes/<id>/scope.json` remains repository scope authority; coordinator state MUST NOT silently replace it.
- Coordinator reservation state owns runtime mutation-authority revision, lease identity, and fence evidence.
- Slice sequencing remains strict: `247 -> 248 -> 249 -> 250 -> 251 -> 252 -> 253`.

## Slice 3 requirements

- **REQ-249-01**: Scope amendment MUST compare-and-swap the current authority revision and fence token; stale writers change no authority state.
- **REQ-249-02**: Every accepted scope/ownership amendment MUST re-run global duplicate/path/shared-coordination validation before repository scope changes.
- **REQ-249-03**: Accepted scope amendments MUST update the existing governed scope through an authoritative CAS adapter and re-read the exact claim before publishing a higher coordinator revision.
- **REQ-249-04**: Lease activation and heartbeat MUST use durable lease identity, holder, issued/expiry timestamps, an injected UTC clock, and exact current revision/fence evidence.
- **REQ-249-05**: Scope revision, lease expiry, and ownership reassignment MUST invalidate stale mutation authority through monotonic authority revision/fence semantics.
- **REQ-249-06**: Mutation-authority validation MUST reject stale revision, holder, lease identity, fence token, or expired lease state before a bounded mutation proceeds.
- **REQ-249-07**: Crash/restart recovery MUST reconstruct authority from append-only journal evidence plus current governed claims and behave deterministically/idempotently.
- **REQ-249-08**: Existing invalid path-conflict claims MUST be partitioned into deterministic connected degraded components with stable affected-path evidence.
- **REQ-249-09**: Intersecting work MUST be blocked while provably disjoint reservations continue through normal governed admission; a globally valid scope repair MAY reconcile the degraded component.
- **REQ-249-10**: Slice 3 remains internal. It MUST NOT implement #250 planning/work packets, #251 workers, #252 reconciliation/integration, or #253 observability/Control Center behavior.

## Acceptance

1. Two concurrent amendments using the same expected revision produce exactly one accepted revision; the stale writer changes no governed or coordinator authority.
2. Global path/shared-claim validation runs before an amendment is accepted and the governed claim re-read matches the proposed scope.
3. Lease activation and heartbeat require exact current reservation/revision/lease/fence/holder evidence.
4. Lease expiry followed by reassignment produces a new lease, higher authority revision, and higher fence token; the old holder is rejected.
5. A fresh authority-service instance reconstructs expired state deterministically and cannot create two valid owners.
6. A pre-existing invalid connected conflict component reports stable affected paths; intersecting reservations are denied and disjoint reservations remain admissible.
7. A valid revision that removes the conflict causes the degraded component to disappear on re-read.
8. Lease and scope-revision results validate against the existing Slice 1 contracts.
9. Coordinator durable state remains inside the declared project boundary.
10. Existing #247/#248 behavior remains green, including cross-thread/process reservation safety.

## Risks and recovery

- Authority transitions share the existing short-lived cross-process admission mutex; worker execution remains outside that lock.
- The current repository change workflow has no generic scope-amend command. Slice 3 therefore uses exact observed-claim CAS through an injected adapter and requires a governed re-read before coordinator revision publication. CAS evidence includes conflict-relevant immutable context such as `outcome` and `excluded_paths`, while only the declared scope fields are mutated.
- Scope transitions persist their full expected/proposed CAS claim evidence before governed mutation and finalize only after re-read. Restart recovery compares that durable evidence with current governed claims rather than reconstructing expected authority from potentially changed state.
- Lease expiry does not release path ownership. Explicit reassignment is required, preventing crash recovery from creating two valid owners.
- Degraded components are authority/recovery evidence in this slice; public projection remains #253.

## Out of scope

- Dependency DAG compilation, actual work-packet production, runtime binding resolution, assignment keys/capability selection, or agent selection (#250).
- Durable worker lifecycle, retry/resume, or MCP worker execution (#251).
- Handoff reconciliation, verification derivation, serialized integration, PR/merge, or cleanup automation (#252).
- Coordinator telemetry, Control Center projection, effectiveness evaluation, operator UX, or commissioning (#253).
- Changes to HR-001, HR-002, HR-003, Work Management implementation, or repository change-governance scripts.
