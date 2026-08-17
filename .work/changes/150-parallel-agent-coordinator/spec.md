# Change Specification: Parallel Agent Coordinator

- **Change ID**: `150-parallel-agent-coordinator`
- **Status**: Slice 6 (#252) active after verified Slice 5 landing
- **Complexity**: `large`
- **Risk triggers**: `architecture_boundary`, `public_contract`, `persistent_state`

## Outcome

Build the KIS-native coordinator as one governed #241 change. Slices #247-#251 are landed. Slice 6 replaces conversational worker handback with deterministic reconciliation, scope/risk-derived verification requirements, and a serialized integration queue while preserving the current KIS-local exact-head landing authority.

## Authority and scope

- Authoritative sources: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, #241, and #252.
- Owned paths remain the parent coordinator contracts/runtime/tests/module spec/change record.
- Reservation/lease/revision/fence state remains the sole mutation-authority plane.
- Runtime/MCP discovery remains advisory; worker `done` remains distinct from repository delivery.
- Slice sequencing remains strict: `247 -> 248 -> 249 -> 250 -> 251 -> 252 -> 253`.
- Change 179 supersedes stale provider-native-CI wording: canonical landing verification is referenced KIS-local exact-head evidence.

## Slice 6 requirements

- **REQ-252-01**: Reconciliation MUST validate packet, assignment generation/key, reservation revision/fence, runtime binding, execution/task identity, and worker status.
- **REQ-252-02**: Reconciliation MUST compare handoff base/head/changed-path claims with independently observed Git evidence.
- **REQ-252-03**: Global claim validity and local packet scope MUST be re-evaluated before a handoff becomes reviewable.
- **REQ-252-04**: Unsatisfied packet dependencies MUST block acceptance without inventing completion evidence.
- **REQ-252-05**: Accepted handoff MUST consume the active assignment key atomically; stale/revoked/consumed keys MUST be rejected.
- **REQ-252-06**: Required checks/reviews MUST derive deterministically from authoritative changed paths, complexity, and risk triggers using repository change-control settings.
- **REQ-252-07**: Verification requirements MUST require the current repository-authoritative KIS-local exact head and MUST NOT require GitHub Actions/provider-native CI.
- **REQ-252-08**: Shared-hotspot/repository landing work MUST enter one durable serialized integration queue owned by the declared integration owner.
- **REQ-252-09**: Integration delivery authorization MUST require referenced passing local verification for the exact candidate head; verification for another SHA MUST fail closed.
- **REQ-252-10**: Slice 6 MUST preserve separate `worker_done`, `reviewable`, `integrating`, `delivered`, `commissioning`, and `closed` semantics and MUST NOT implement #253 observability/UX.

## Acceptance

1. Stale reservation/fence/runtime/assignment or mismatched observed Git evidence is rejected deterministically.
2. Out-of-scope changed paths and invalid current global claims block reviewability.
3. Exact duplicate accepted reconciliation is idempotent; a consumed key cannot authorize a different handoff.
4. Verification requirements are stable for identical authoritative inputs and map configured risk triggers to configured review types.
5. The verification contract represents `kis_local_exact_head` authority and no longer encodes provider-native CI as a requirement.
6. Integration queue admission is single-owner and serialized across concurrent contenders.
7. Delivery authorization rejects missing, failed, stale, unreferenced, or non-local exact-head verification evidence.
8. Existing #247-#251 coordinator regression tests remain green.

## Risks and recovery

- Reconciliation evidence is durable generated state and must stay beneath the configured `C:\Projects` state boundary.
- Assignment consumption and integration queue mutation require cross-process serialization so crash/retry cannot create two valid owners.
- Rejected/incomplete worker handoff never implies repository rollback; it records deterministic residual state for repair/reassignment.
- Actual GitHub merge remains the existing registered KIS exact-head merge operation. Slice 6 authorizes/serializes the candidate; it does not create a competing GitHub client.

## Out of scope

- #253 telemetry, Control Center projection, effectiveness evaluation, operator UX, and live commissioning.
- Replacing existing GitHub registered merge/refresh/cleanup primitives.
- Reintroducing GitHub Actions as a canonical landing requirement.
- Work Management view commissioning or unrelated active lanes.
