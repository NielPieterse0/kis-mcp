# Change Specification: Project Tasks Improvement Programme

- **Change ID**: `140-project-tasks-improvement-programme`
- **Programme issue**: #215
- **Slices**: #216, #217, #218, #219
- **Complexity**: large
- **Risk triggers**: persistent_state, public_contract, architecture_boundary, deployment

## Outcome

Deliver four ordered improvements without creating a second authority model:

1. make remote runtime readiness generation-aware and prove MCP initialization before `current.json` can report ready;
2. add a symmetrical current/resume workflow for already-claimed Active work;
3. expose one normalized, active-first Work board projection and make Control Center consume that projection;
4. make project-management tool results, typed failures, annotations, provenance, freshness, completeness and next-action guidance consistent.

## Authority and constraints

- Preserve `.work`, Git/GitHub, configured Work Management backend, and provider-native verification as their existing authorities.
- Keep TaskPlanner as planning guidance only; do not create `.tasks` or another durable Work truth.
- Preserve exactly HR-001, HR-002 and HR-003.
- Keep mutations explicit, bounded and idempotency-keyed.
- Do not touch the active recovery-capsule change's likely domains: `src/kis_mcp/evidence/**`, project identity/registry, or repo-local `.temp/kis` state.
- Maintain backward compatibility for existing project-management calls where practical; additive envelopes must retain the existing result payload under a stable `result` member or preserve existing top-level fields during migration.
- Control Center remains read-only.

## Slice 1 — Runtime generation identity and live-state reconciliation (#216)

### Requirements

- Persist source revision, contract fingerprint, policy fingerprint and explicit successful MCP initialize evidence in ready runtime state.
- A `ready` marker is valid only when instance, endpoint, live listener PID, source revision and contract generation match the serving process.
- Legacy/stale/mismatched markers must not upgrade health to external-tunnel-ready.
- Restart, failed-start, stop and replacement semantics remain atomic and run-ID guarded.
- No credentials or secret values are persisted.

### Acceptance

- Matching generation reports ready.
- Stale source revision, contract fingerprint, initialization evidence, PID, endpoint, instance or lifecycle is rejected as stale/not-ready.
- Focused startup/operational-status tests pass.

## Slice 2 — Current/resume work workflow (#217)

### Requirements

- Add a read-only operation that finds Active work by project and execution owner.
- Return deterministic none/one/multiple outcomes; never guess when multiple claims exist.
- For exactly one Active issue, reconstruct source identity, Work State, execution owner and available Work Management metadata, then return bounded next valid actions.
- Preserve existing claims; resume never reacquires or mutates the claim.
- Truncated inventory or provider failure remains explicitly incomplete/unavailable.

### Acceptance

- Tests cover none, one, multiple, stale/invalid source, and truncated inventory.
- The new MCP tool is explicitly read-only and non-destructive.

## Slice 3 — Normalized Work board + Control Center (#218)

### Requirements

- Add one typed board view model built from Project inventory, not a duplicate persistence layer.
- Default to active states and bounded history; expose counts, cards, freshness/provenance, completeness/truncation and next-work/current-work signals.
- Cards include project, repository, issue number, title, state, owner, priority, effort, change ID, delivery/verification metadata when present, and blocker evidence.
- Support bounded query/state/owner grouping/filtering without provider mutation.
- Control Center consumes the same board payload through an injected read-only source and degrades independently if Work Management is unavailable.

### Acceptance

- Projection/filter/group tests pass.
- Control Center exposes the same board schema rather than independently interpreting Project fields.

## Slice 4 — Work Management UX and contract hardening (#219)

### Requirements

- Add a consistent operational response envelope containing observation time, resolved target, authority/provenance, completeness/truncation/warnings, result and bounded next actions.
- Normalize typed project-management failures so provider unavailable, project uncommissioned, stale/incomplete inventory, conflict and invalid transition are distinguishable.
- Add accurate MCP tool annotations/hints for read-only and mutating project-management operations.
- Keep existing callers compatible: domain result payloads remain machine-readable and no mutation gains implicit apply authority.

### Acceptance

- Tool contract tests cover annotations, envelopes, error typing, provenance and compatibility.
- Existing Work Management tests remain green.

## Documentation and completion

Reconcile current behavior into `SPEC.md` and operator startup/status behavior into `docs/OPERATIONS.md`. Exact-head canonical CI is mandatory. Because this host cannot invoke local KIS runtime commissioning, do not claim live post-merge commissioning unless provider-native evidence or a later KIS-enabled session performs it.
