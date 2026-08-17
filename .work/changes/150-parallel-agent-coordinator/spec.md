# Change Specification: Parallel Agent Coordinator

- **Change ID**: `150-parallel-agent-coordinator`
- **Status**: Slice 5 (#251) implementation complete locally — current-main reconciliation and canonical local exact-head verification/merge pending
- **Complexity**: `large`
- **Risk triggers**: `architecture_boundary`, `public_contract`, `persistent_state`

## Outcome

Build the KIS-native coordinator as one governed #241 change. Slices #247-#250 established contracts, reservation/fencing authority, deterministic planning, runtime binding, and bounded work packets. Slice 5 adds durable-execution semantics and an MCP worker adapter, but new persistence MUST consume #278 state ownership/namespace authority rather than inventing a coordinator-local location scheme.

## Authority and scope

- Authoritative sources: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, #241, #251, and #278.
- Owned implementation paths remain the parent coordinator contracts/runtime/tests/module spec/change record.
- Slice 3 reservation/lease/fence state remains the sole mutation-authority plane.
- Runtime/MCP discovery and connectivity remain ephemeral advisory execution state.
- Slice sequencing remains strict: `247 -> 248 -> 249 -> 250 -> 251 -> 252 -> 253`.
- #278 owns durable state class identity and namespace resolution. #251 consumes the landed typed ownership/resolver/source-identity APIs directly and MUST NOT duplicate them.

## Slice 5 requirements

- **REQ-251-01**: Worker lifecycle MUST model `pending`, `running`, `waiting_input`, `completed`, `failed`, `cancelled`, and `recoverable` states with deterministic transitions.
- **REQ-251-02**: Execution identity MUST correlate packet, assignment generation, reservation revision/fence, runtime binding, attempt, progress, and result identifiers without treating transport/session IDs as authority.
- **REQ-251-03**: Duplicate/stale lifecycle events MUST be idempotent when byte-equivalent or rejected deterministically when they conflict.
- **REQ-251-04**: MCP connection, discovery, reconnect, and cleanup MUST be ephemeral and MUST NOT create, refresh, transfer, or recover mutation authority.
- **REQ-251-05**: Tool exposure and invocation MUST be filtered before model execution against the bounded work packet/capability policy and re-check active reservation authority before mutating execution.
- **REQ-251-06**: MCP adapter behavior MUST cover connect/discover/filter/invoke/progress/result/cleanup/reconnect through injected transport interfaces, with bounded normalized results.
- **REQ-251-07**: Worker result/handoff MUST correlate to the exact execution, reservation revision/fence, runtime-binding fingerprint, exact head, changed paths, evidence, and deterministic residual state.
- **REQ-251-08**: Restart/recovery persistence MUST store only durable execution facts and MUST use #278's typed durable-evidence ownership class and deterministic namespace resolver.
- **REQ-251-09**: Recreated runtime/MCP connections after restoration MUST re-establish transport only; mutation execution requires the same current Slice 3 authority assertion.
- **REQ-251-10**: Slice 5 MUST NOT implement #252 handoff reconciliation/key consumption/integration or #253 observability/commissioning.

## Acceptance

1. Lifecycle state and transition contracts reject invalid/stale transitions deterministically and accept exact duplicate observations idempotently.
2. Execution records contain stable packet/reservation/runtime correlation and explicit attempt/progress/result identifiers without making session identity authoritative.
3. MCP tool discovery is filtered before execution; a tool not admitted by the packet/capability policy cannot be invoked through the adapter.
4. Runtime reconnect/list-tools operations cannot grant mutation authority and do not mutate durable execution state by themselves.
5. A mutating invocation re-checks current reservation/revision/lease/fence authority immediately before dispatch.
6. Completed/failed/cancelled outcomes produce deterministic structured result/handoff facts suitable for #252 without claiming reconciliation.
7. Persistence/restart tests prove the #278 `DURABLE_EVIDENCE` resolver/source-identity contract is used, ordered execution state restores after restart, completed mutation retries reuse durable results, and uncertain in-flight mutation work is not replayed automatically.
8. Existing #247-#250 coordinator tests remain green.

## Risks and recovery

- Existing Slice 2-4 generated-state locations are historical implementation facts and are not precedent for new #251 durable state placement after #277/#278 architecture approval.
- Transport clients/sessions are process-local and reconstructible. Durable records may retain correlation identifiers but never live transport objects.
- Mutation safety depends on Slice 3 authority checks, not MCP connectivity or discovered tool metadata.
- #278 was the persistence/restart dependency and is now satisfied by the landed ownership/namespace module; future coordinator state must continue consuming that canonical module rather than reintroducing local placement rules.

## Out of scope

- Implementing, modifying, or pre-empting #278 state ownership classes/namespace resolution.
- #252 assignment-key consumption, handoff reconciliation, verification derivation, integration serialization, PR/merge, or cleanup automation.
- #253 telemetry, Control Center projection, operator UX, effectiveness evaluation, or commissioning.
- Work Management view commissioning, GitHub mutation receipt work, source-isolation work, or other active lanes.
