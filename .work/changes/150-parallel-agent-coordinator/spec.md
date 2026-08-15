# Change Specification: Parallel Agent Coordinator

- **Change ID**: `150-parallel-agent-coordinator`
- **Status**: Slice 4 (#250) complete — parent change remains active
- **Complexity**: `large`
- **Risk triggers**: `architecture_boundary`, `public_contract`

## Outcome

Build the KIS-native coordinator as one governed #241 change. Slices #247-#249 established contracts, atomic reservation admission, and revision-safe mutation authority. Slice 4 (#250) adds deterministic read-only planning, bounded work-packet issuance, opaque assignment-key evidence, and exact runtime/capability binding without entering worker execution.

## Authority and scope

- Authoritative sources: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, #241, and #250.
- Owned implementation paths remain the parent coordinator contracts/runtime/tests/module spec/change record.
- Governed scope and Slice 3 reservation/lease/fence state remain mutation authority.
- Registry/catalog discovery is advisory evidence only and MUST NOT create or refresh authority.
- Slice sequencing remains strict: `247 -> 248 -> 249 -> 250 -> 251 -> 252 -> 253`.

## Slice 4 requirements

- **REQ-250-01**: Planner output MUST be deterministic for the same authoritative task, scope, dependency, and base inputs; planning MUST NOT require mutation authority.
- **REQ-250-02**: Planning MUST validate dependency endpoints and cycles before producing a dependency DAG.
- **REQ-250-03**: Planning MUST reject unresolved exclusive ownership and shared hotspots without exactly one integration owner.
- **REQ-250-04**: Planner output MUST expose the ready frontier, integration hotspots, sequencing edges, and bounded recommended concurrency.
- **REQ-250-05**: Work packets MUST freeze outcome, scope, dependencies, acceptance checks, exact base, reservation/revision/lease/fence identity, runtime binding, verification requirement IDs, and required handoff fields.
- **REQ-250-06**: Initial packet issuance MUST create a stable packet identity plus one opaque assignment key and persist only the key digest as durable authority evidence.
- **REQ-250-07**: Runtime/capability resolution MUST deterministically select an exact worker/runtime/tool/protocol/interface/endpoint/binding identity that satisfies required capabilities.
- **REQ-250-08**: Runtime binding evidence MUST state `grants_mutation_authority=false`; discovery candidates cannot bypass reservation authority.
- **REQ-250-09**: Canonical shared files SHOULD be represented as explicit integration hotspots rather than ambiguous concurrent exclusive ownership.
- **REQ-250-10**: Slice 4 remains internal. It MUST NOT implement #251 worker lifecycle/execution, #252 reconciliation/integration, or #253 observability/commissioning.

## Acceptance

1. Repeating a plan with identical inputs produces byte-equivalent canonical DAG data.
2. Cycles, missing dependency endpoints, duplicate task IDs, and unresolved path ownership are rejected deterministically.
3. Independent ready leaves are visible together; hotspot overlap reduces recommended concurrency.
4. Every shared hotspot records one integration owner and all participating tasks.
5. Issued packets validate against the work-packet schema and contain all execution/handoff facts needed without chat context.
6. Packet IDs are stable for the same frozen work identity; assignment keys are opaque and durable state retains only their digest.
7. Runtime bindings validate against the runtime-binding schema and freeze exact worker/runtime/tool/protocol/interface/endpoint/binding evidence.
8. A discovery candidate that claims mutation authority is rejected; reservation/lease/fence authority remains unchanged.
9. Existing #247-#249 coordinator tests remain green.
10. No worker execution, reconciliation, integration, telemetry, public coordinator MCP surface, or landing behavior is added.

## Risks and recovery

- Planning and runtime selection remain pure/read-only over supplied authoritative evidence; only packet issuance writes bounded generated coordinator state.
- Packet durable state stores assignment-key hashes, not plaintext keys. A lost plaintext key requires later reassignment rather than recovery from storage.
- Stable packet identity is derived from logical work, exact base, scope, acceptance, and verification inputs; lease/fence/runtime changes do not rename the packet, and assignment generation remains separate.
- Runtime discovery freshness is caller-supplied evidence. The resolver validates exact identity and capabilities but does not infer authority from connectivity.

## Out of scope

- Durable worker lifecycle, retry/resume, MCP worker execution, or transport session ownership (#251).
- Handoff reconciliation, assignment-key consumption, verification derivation, serialized integration, PR/merge, or cleanup automation (#252).
- Coordinator telemetry, Control Center projection, effectiveness evaluation, operator UX, or commissioning (#253).
- Changes to HR-001, HR-002, HR-003, Work Management implementation, or repository change-governance scripts.
