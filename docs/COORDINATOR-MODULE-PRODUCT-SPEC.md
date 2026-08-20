# Coordinator Module Product Specification

## Authority boundary

This document owns the long-lived target architecture and contract map for KIS parallel-agent coordination. It is subordinate to `AGENTS.md`, `docs/TRUST-MODEL.md`, root `SPEC.md`, and `docs/PLATFORM-CONCEPT.md`.

Root `SPEC.md` remains authoritative for repository-wide current product behavior. This module specification specializes the reconstructed coordinator scope; contract presence alone does not imply behavior beyond the runtime and tests landed with Change 193.

## Outcome

The coordinator makes parallel repository implementation mechanically safe and recoverable without relying on chat history for ownership or handoff facts.

The system must preserve both:

- **safety** — conflicting mutation authority cannot be acquired concurrently; and
- **liveness** — an invalid or conflicting component cannot globally block provably disjoint work.

The coordinator is one governed #241 repository change delivered through dependent slices `247 -> 248 -> 249 -> 250 -> 251 -> 252 -> 253`.

## Non-policy status

Coordinator admission, readiness, leases, verification, and integration state are workflow authority. They do not add a fourth Work hard rule.

Concrete Work invocations remain subject only to HR-001, HR-002, and HR-003 as defined by `docs/TRUST-MODEL.md` and `policy/kis-mcp.policy.json`.

## Four authority planes

### 1. Registry and discovery

Describes available projects, agents, MCP servers, tools, skills, endpoints, revisions, and capabilities. This plane is advisory evidence only.

Discovery or successful connection MUST NOT grant repository mutation authority.

### 2. Deterministic mutation authority

Owns reservation identity, exclusive/shared path claims, dependency evidence, integration ownership, authority revision, lease identity, and fencing token.

Only this plane may determine whether a worker currently holds valid mutation authority. Later slices must implement every authority mutation as an explicit deterministic transition.

### 3. Ephemeral execution transport

Carries runtime connection state such as MCP/A2A/local-process identity, tool discovery, progress, and session objects.

Transport may be recreated after restart. A reconnect MUST NOT create, renew, transfer, or recover mutation authority by itself.

### 4. Durable execution and evidence

Persists bounded worker lifecycle, exact base/head identity, changed paths, handoff evidence, verification requirements, reconciliation facts, and closeout state.

Durable evidence supports recovery but cannot override a newer reservation revision or fencing token.

## Coordinator state model

The authoritative coordinator lifecycle distinguishes these states:

| State | Meaning |
|---|---|
| `planning` | Read-only dependency/scope analysis; no mutation authority. |
| `reserved` | Deterministic reservation exists with exact base, revision, lease, and fence evidence. |
| `executing` | A bounded worker is operating under the reservation. |
| `handed_off` | Worker produced structured evidence; no verification or merge claim follows automatically. |
| `reconciling` | Handoff is being checked against reservation, fence, global claims, local scope, and exact head. |
| `reviewable` | Reconciliation and required pre-review gates permit review preparation. |
| `integrating` | Central integration owner serializes a shared-hotspot or landing operation. |
| `delivered` | Repository landing is evidenced; live commissioning may remain. |
| `commissioning` | Landed behavior is undergoing required live acceptance. |
| `closed` | All required repository, commissioning, projection, and cleanup gates are complete. |
| `degraded` | One bounded conflict/invalid component exists; disjoint admission remains possible. |
| `failed` | The current transition cannot continue without corrective action. |

`worker_done` is a worker-handoff status, not a coordinator lifecycle terminal state. It MUST NOT be treated as `reviewable`, `delivered`, `commissioning`, or `closed`.

## Executable contract ownership

The coordinator contract catalogue contains eleven strict Draft 2020-12 schemas beneath `contracts/coordinator/`. Change 193 retains the location-independent `worker-execution` contract and versions verification requirements to the current provider-native GitHub Actions exact-head landing authority:

| Contract | Purpose | Behavioral owner |
|---|---|---|
| `coordinator-state` | Lifecycle and degraded-component projection. | #253 projection after underlying slices exist. |
| `reservation` | Frozen mutation-authority identity and path/dependency claims. | #248 |
| `lease` | Lease holder, expiry, and fencing identity. | #249 |
| `scope-revision` | Compare-and-swap inputs for explicit scope changes. | #249 |
| `dependency-dag` | Candidate dependency graph and shared-hotspot ownership; Slice 1 cannot self-assert graph verification. | #250 validates endpoints/cycles and produces planner evidence. |
| `runtime-binding` | Canonical exact runtime/tool/transport identity with mutation authority fixed false. | #250 produces/revises; #251 consumes its immutable reference. |
| `work-packet` | Bounded worker assignment with frozen authority, task/capability correlation, and immutable reference to the canonical runtime binding. | #250/#251 |
| `worker-execution` | Location-independent worker lifecycle, authority/runtime correlation, idempotent event identity, and progress/result identifiers. | #251 |
| `worker-handoff` | Exact worker output/evidence, execution/attempt/result correlation, and residual state. | #251 |
| `verification-requirements` | Scope/risk-derived gate requirements without pass claims; v3 fixes canonical landing authority to referenced provider-native GitHub Actions verification for the exact candidate head. | Change 193 reconstruction of #252 |
| `reconciliation-result` | Deterministic handoff validation and integration disposition. | #252 |

Slice 1 publishes the schemas only as repository-owned contract resources under `contracts/coordinator/`; it exposes no runtime coordinator package or MCP tool. Runtime loading/validation belongs to the later slice that implements the consuming behavior, so Slice 1 does not couple contract access to a source-checkout layout.

Every contract is closed at its object boundaries. Contract expansion therefore requires an explicit versioned/governed change rather than arbitrary runtime fields.

## Mutation-authority invariants

Later implementations must preserve all of these invariants:

1. One globally unique human-facing change sequence identifies each active governed change.
2. One active mutation authority may own an exclusive path at a time.
3. Shared paths require explicit dependency or integration ownership.
4. Scope expansion is an authority revision, never an unvalidated worker edit.
5. A stale authority revision or fencing token cannot mutate, reconcile successfully, or integrate.
6. Runtime/registry discovery never implies authority.
7. A worker handoff is rejected when its reservation, fence, exact head, changed scope, or evidence is stale or inconsistent.
8. Verification requirements derive from authoritative scope/risk facts rather than worker confidence.
9. Shared-hotspot integration is centrally serialized through the declared integration owner.
10. Canonical repository landing requires referenced passing provider-native GitHub Actions verification for the exact candidate head.

The contract catalogue records the evidence needed to evaluate these invariants. Slices 2 through 6 now implement reservation, authority, planning, worker execution, reconciliation, verification derivation, and serialized integration transitions; #253 remains responsible for projection and commissioning.

## Degraded-component semantics

A conflict graph may contain an invalid component while unrelated work remains valid. Coordinator state therefore models degraded components explicitly instead of reducing the entire repository to one blocked flag.

Each degraded component is keyed by its stable component identity and requires non-empty affected paths plus nested reservation checks. At least one nested reservation check must intersect the component, so the component cannot be empty or detached from all affected work. Each check is therefore structurally scoped to a declared component and couples `intersects_degraded_component` to `blocked_by_component` versus `clear_of_component`.

A component check is not final admission. A later admission implementation owns computation of the intersection fact and all other admission constraints. Work that is clear of one degraded component must continue through normal evaluation and may still be blocked for an independent reason.

## Historical acceptance scenarios

`contracts/coordinator/examples/degraded-overlap.json` represents the observed 140/145 failure: both changes held exclusive claims over shared canonical paths including `src/kis_mcp/capabilities/surface.py`, `SPEC.md`, and `docs/OPERATIONS.md`.

The example intentionally records this as one degraded conflict component. It does not authorize either claimant and does not convert the conflict into a repository-wide stop.

`contracts/coordinator/examples/disjoint-admission.json` represents the liveness requirement exposed when change 148 had to use an emergency manual worktree after an unrelated global claim conflict.

The target outcome is explicit: a disjoint reservation such as the narrow GitHub Project adapter change remains admissible while the 140/145 conflict component is degraded.

These fixtures remain architecture acceptance evidence. Slice 2 executes reservation admission, and Slice 3 now derives connected degraded components from current governed claims, blocks only intersecting reservations, and permits a globally valid scope amendment to repair an affected component. Public degraded-state projection remains #253.

## Planned implementation ownership

| Slice | Issue | Owned behavior after implementation |
|---|---|---|
| 1 | #247 | Architecture, schemas, scenario contracts, ownership map. |
| 2 | #248 | Atomic reservation, unique sequence allocation, global claim admission. |
| 3 | #249 | CAS scope revisions, leases, fencing, expiry/reassignment, recovery. |
| 4 | #250 | Dependency planner, bounded work packets, runtime/capability resolution. |
| 5 | #251 | Durable worker lifecycle, retry/resume, MCP worker adapter. |
| 6 | #252 | Handoff reconciliation, verification derivation, integration serialization. |
| 7 | #253 | Coordinator observability, effectiveness evaluation, operator UX, commissioning. |

## Slice sequencing and integration

The default dependency chain is strict:

```text
247 -> 248 -> 249 -> 250 -> 251 -> 252 -> 253
```

No implemented slice grants an exception to this dependency chain: the remaining slices proceed sequentially under the single parent change. A future overlap is permitted only if a later landed authority mechanism explicitly records a governed sequence exception with prerequisite revision and landed-base evidence; conversational scope judgment alone is insufficient.

Separate issue numbers are acceptance units, not independent worktrees. The single parent governed change remains the integration owner for coordinator-specific shared hotspots until an explicit governed revision changes that strategy.

## Cumulative implementation status through Slice 6

Implemented by #247:

- the ten strict coordinator JSON Schema contracts;
- executable degraded-overlap/disjoint-liveness examples;
- the four-plane architecture, state model, ownership map, and slice sequence.

Implemented by #248 on the parent change branch:

- an internal reservation service with a cross-process admission mutex;
- unique sequence allocation across active claims, historical change records, and consumed reservation-journal evidence;
- deterministic duplicate/exclusive/shared claim admission checks;
- append-only pending/reserved/aborted/degraded reservation evidence bounded by the declared project boundary;
- exact-base capture and initial `authority_revision=1`, lease identity, and `fence_token=1` issuance;
- configured Work Management claim/compensation ports inside the serialized transaction;
- delegation of branch/worktree creation to the existing governed change workflow, followed by claim identity re-read.

Implemented by #249 on the same parent branch:

- compare-and-swap scope revision using exact current authority revision and fence evidence;
- authoritative governed-scope amendment through an injected adapter plus exact post-mutation claim re-read before coordinator revision acceptance, with full CAS evidence for `outcome`, `excluded_paths`, and the mutable scope fields;
- append-only authority transition evidence, persisted expected/proposed CAS endpoints, numeric journal ordering beyond three-digit event ordinals, and deterministic restart recovery from durable reservation state plus current governed claims;
- lease activation, heartbeat, expiry, reassignment, and exact holder/revision/lease/fence mutation-authority checks using an injected UTC clock;
- monotonic authority/fence invalidation of stale holders after scope changes, expiry, or reassignment;
- deterministic connected degraded conflict components that block intersecting reservations while preserving disjoint admission;
- rejection of semantically empty revisions and enforcement of explicit coordination before an owned-only reservation adds its first shared path;
- valid scope repair of an intersecting degraded claim when the resulting global claim set is conflict-free;
- a Windows-safe shared admission-lock initialization path used by both reservation and authority transitions.

Implemented by #250 on the same parent branch:

- a deterministic read-only planner that validates dependency endpoints/cycles and rejects unresolved exclusive ownership or ambiguous shared-hotspot ownership;
- canonical dependency DAG output with ready-frontier, sequencing/integration edges, explicit hotspot evidence, and bounded recommended concurrency;
- exact runtime/capability resolution through injected discovery evidence, recording worker, runtime, tool, protocol, interface, endpoint, binding, versions/revisions, capabilities, observation time, and an immutable binding fingerprint;
- runtime binding contracts that structurally fix `grants_mutation_authority=false`, so registry/tool discovery remains advisory rather than an authority source;
- bounded work-packet issuance that freezes Slice 3 reservation/revision/lease/fence authority, exact base, scope, dependencies, acceptance checks, verification requirements, runtime binding, and required handoff fields;
- stable packet identity plus generation-1 opaque assignment-key issuance, with only the SHA-256 key digest retained in durable coordinator evidence;
- generated packet/runtime-binding state constrained to the configured coordinator state root inside the project boundary.

Implemented by #251 on the same parent branch:

- `coordinator-worker-execution-v2`, a strict location-independent execution contract covering packet/task/assignment/reservation/fence/runtime/attempt correlation, lifecycle state, progress/result IDs, residual state, and accepted-event identity evidence;
- deterministic worker transitions for `pending`, `running`, `waiting_input`, `completed`, `failed`, `cancelled`, and `recoverable`, including idempotent replay of any accepted exact event and stale/conflicting event rejection;
- `coordinator-worker-handoff-v2` execution/attempt/task/result correlation without performing #252 reconciliation or assignment-key consumption;
- `coordinator-work-packet-v2` task/capability correlation so tool exposure remains tied to the bounded planner task;
- an internal ephemeral MCP worker adapter that validates the exact runtime binding, filters discovery to the exact work packet, classifies mutation from tool metadata plus concrete arguments, re-checks current reservation/revision/lease/fence authority immediately before mutation, normalizes bounded results, and clears exposure on reconnect;
- an internal durable `WorkerExecutionStore` that consumes landed #278 directly: `StateOwnershipClass.DURABLE_EVIDENCE`, `StateNamespaceRequest`, `StateNamespaceResolver`, and `derive_change_source_id(change_id)` determine the only execution-evidence namespace; #251 defines no alternate state root or source naming convention;
- restart restoration of ordered accepted-event history, preserving deterministic sequence/conflict checks and idempotent persisted resume/retry;
- durable mutation receipts keyed to execution/result identity and fingerprinted over execution/attempt, reservation/revision/lease/fence authority, runtime binding, tool, arguments, progress, and result identifiers;
- a write-ahead mutation receipt before MCP dispatch: a completed receipt returns the previously normalized result without re-executing the mutation, while an `in_flight` receipt after interruption fails closed for explicit reconciliation rather than risking duplicate mutation;
- per-execution cross-process serialization around lifecycle snapshot transitions so conflicting same-sequence updates cannot silently overwrite one another;
- structured adapter results retain execution/attempt, exact authority facts, runtime binding, packet/task, progress, and result correlation when durable execution identity is supplied;
- reconnect, discovery, and transport session state remain ephemeral and non-authorizing; durable evidence never creates, renews, or supersedes #248/#249 mutation authority.

Hardened by #412 / Change 215:

- `coordinator-work-packet-v3` adds stable packet/task lineage plus generation-specific `run_id`, predecessor-run lineage, explicit executor/profile, exact governed root/worktree/base/lifecycle envelope, authority references, Work Management identity, and bounded external provenance;
- `coordinator-worker-execution-v3` and `coordinator-worker-handoff-v3` carry the same project/change/run/worktree/lifecycle identity so stale or cross-assignment evidence cannot be mistaken for the active run;
- reassignment is an explicit generation transition that requires the same reservation with a strictly higher authority revision/fence and a new lease, records the predecessor run as revoked, and issues a new opaque assignment key/run identity;
- workers re-check current authority before tool exposure and immediately before mutation, while reconciliation cross-checks run/project/change/worktree/lifecycle identity against durable packet and execution evidence.

Reconstructed by Change 193 from the retained #252 behavior:

- deterministic handoff reconciliation against durable packet issuance, assignment generation/key digest, current reservation revision/fence, runtime binding, worker/task identity, independently observed exact base/head, changed paths, current global claims, local packet scope, and dependency completion;
- assignment consumption only after accepted reconciliation has secured serialized integration admission, with exact replay idempotence and rejection of stale or differently consumed assignments;
- scope/risk-derived verification requirements that reuse canonical change-control settings for configured review types and version the contract to `coordinator-verification-requirements-v3`;
- canonical verification authority fixed to referenced passing provider-native GitHub Actions evidence for the exact candidate head;
- durable reconciliation and integration evidence placed through the current `DURABLE_EVIDENCE` namespace resolver and governed change source identity;
- a cross-process serialized integration queue that admits one active candidate per integration owner, requires exact-head GitHub Actions verification before delivery authorization, and records delivered merge identity without duplicating the existing registered GitHub merge client;
- fail-closed behavior for tampered packet evidence, stale authority, out-of-scope changes, invalid global claims, unsatisfied dependencies, busy integration owners, and stale verification evidence.

The reconstructed coordinator exposes no public MCP coordinator tool. Transport discovery/connectivity never grants authority.

Out of scope for Change 193:

- historical #253 coordinator telemetry, Control Center projection, effectiveness evaluation, operator UX, or live commissioning;
- any local, VM, VirtualBox, or disposable-Windows replacement for canonical GitHub Actions verification.
