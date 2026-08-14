# Change Specification: Parallel Agent Coordinator

- **Change ID**: `150-parallel-agent-coordinator`
- **Status**: Active — Slice 1 only
- **Complexity**: `large`
- **Risk triggers**: `architecture_boundary`, `public_contract`

## Outcome

Build the KIS-native coordinator as one governed #241 change. This slice defines the authoritative architecture and executable contracts required by #247; later slices implement behavior against those contracts.

## Authority and scope

- Authoritative sources: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, #241, and #247.
- Owned paths: `contracts/coordinator/**`, `src/kis_mcp/workflows/coordinator/**`, `tests/workflows/coordinator/**`, `docs/COORDINATOR-MODULE-PRODUCT-SPEC.md`, and this change record.
- Shared paths: none.
- Excluded: current Skills telemetry, review-backend, GitHub Project adapter, external-acquisition, policy, `SPEC.md`, and `docs/OPERATIONS.md` paths.
- Dependency: later slices consume this contract set; Slice 1 does not implement mutation authority or worker execution.

## Requirements

- **REQ-001**: Define four distinct planes: registry/discovery, deterministic mutation authority, ephemeral execution transport, and durable execution/evidence.
- **REQ-002**: Define coordinator lifecycle states without equating worker completion, reconciliation, reviewability, repository delivery, commissioning, or closure.
- **REQ-003**: Provide strict Draft 2020-12 schemas for work packet, reservation, lease/fence, scope revision, dependency DAG, runtime binding, worker handoff, verification requirements, reconciliation result, and coordinator state.
- **REQ-004**: Runtime/tool discovery and connectivity MUST be structurally non-authorizing.
- **REQ-005**: Degraded conflict state MUST identify the affected component and explicitly preserve admission of provably disjoint work.
- **REQ-006**: Every mutation-relevant record MUST carry exact identity/revision/fence evidence sufficient for later deterministic validation; runtime-binding ID/fingerprint evidence persists from work packet through worker handoff and reconciliation; the contract itself grants no mutation authority.
- **REQ-007**: Preserve #241 sequencing `247 -> 248 -> 249 -> 250 -> 251 -> 252 -> 253`; Slice 1 grants no sequence exception and MUST NOT implement later-slice services.
- **REQ-008**: Represent the historical 140/145 overlap and unrelated-work liveness failure as executable contract scenarios.

## Acceptance

1. **Given** the repository-owned coordinator contract directory, **when** every schema is validated, **then** exactly ten strict Draft 2020-12 schemas exist with stable KIS contract identities and no Slice-1 runtime coordinator package.
2. **Given** an execution runtime binding, **when** validated, **then** it cannot claim or imply repository mutation authority.
3. **Given** a worker handoff, **when** validated, **then** `worker_done` remains distinct from reconciliation, reviewability, delivery, commissioning, and closure.
4. **Given** overlapping 140/145-style exclusive claims, **when** represented as degraded state, **then** the affected component is explicit and disjoint admission remains allowed.
5. **Given** a disjoint reservation scenario, **when** validated beside a degraded conflict component, **then** the contract contains no global-stop semantics.
6. **Given** later-slice implementation, **when** consuming Slice-1 contracts, **then** reservation revisions, lease/fence identity, exact base/head evidence, runtime identity, verification requirements, and integration ownership have unambiguous fields.

## Risks and recovery

- Risk: contracts drift into an alternate authority or prematurely encode implementation behavior.
- Recovery: JSON Schema remains structural only; repository/Git/Work authorities remain unchanged, and later slices may version contracts through governed scope revisions rather than silently changing semantics.
- Risk: active parallel changes claim canonical shared files.
- Recovery: this slice uses only coordinator-specific paths and does not modify current shared hotspots.

## Out of scope

- Atomic reservation/admission implementation (#248).
- CAS scope mutation, active lease enforcement, fencing, and recovery (#249).
- Planner/work-packet production, runtime resolution, or agent selection (#250).
- Durable worker process/task execution or MCP adapter (#251).
- Reconciliation execution, verification selection, integration queue, PR/merge, or cleanup automation (#252).
- Coordinator telemetry, Control Center integration, evaluation, or live commissioning (#253).
