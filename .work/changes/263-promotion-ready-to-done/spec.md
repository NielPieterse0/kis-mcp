# Change Specification: PromotionReady-to-Done Convergence

- **Change ID**: `263-promotion-ready-to-done`
- **Status**: Active
- **Work**: `WORK-585` / issue `#585`
- **Complexity**: `large`
- **Risk triggers**: `architecture_boundary`, `external_action`, `persistent_state`, `public_contract`

## Outcome

Expose one durable, bounded `converge_change_to_done` MCP operation that consumes a persisted PromotionReady handoff and deterministically carries the governed change through registered GitHub promotion, exact-head CI, Work merge readiness, merge, documentation reconciliation, Work completion, and cleanup without restarting KIS substantive implementation review.

## Authority and scope

- Repository authority: `AGENTS.md`, current `SPEC.md`, current machine contracts and tests.
- Source Work authority: `#585`, child of programme `#584` / `#492`.
- Existing once-through contracts/controller remain the implementation base; do not create a second workflow authority.
- Durable KIS checkpoint state, Work Management, registered GitHub truth, and provider-native Actions evidence remain authoritative.
- MCP Task identity is transport-facing only and never replaces Work/change/checkpoint identity.

## Requirements

- **REQ-001 — Public convergence operation:** register `converge_change_to_done` as a bounded public MCP tool over a persisted PromotionReady Work identity.
- **REQ-002 — Durable task execution:** expose the operation with the existing optional MCP Tasks configuration and synchronous fallback.
- **REQ-003 — Stateful deterministic stages:** production convergence must use `PromotionController`; persisted ordered checkpoints are the sole stage-resume authority and completed stages must not replay.
- **REQ-004 — Stage evidence continuity:** each stage may consume exact observations produced by earlier completed stages; persisted observations must survive resume and remain handoff-fingerprint bound.
- **REQ-005 — Authoritative reconciliation:** every external mutation must be preceded or guarded by current authoritative identity evidence and must safely recognize already-applied exact state after timeout/response loss.
- **REQ-006 — No duplicate implementation review:** after PromotionReady, convergence must never invoke `execute_change_workflow`, `review_change_with_agent`, or another KIS substantive implementation review.
- **REQ-007 — Exact-head landing gates:** provider-native GitHub Actions evidence for the exact pull-request head and Work Management merge readiness remain mandatory before merge.
- **REQ-008 — Exception semantics:** pending or genuinely blocked stages must persist a precise stage/result checkpoint and return resumable structured state; missing human judgement/input must be represented as an exception state rather than implicit approval or workflow reset.
- **REQ-009 — Governed terminal sequence:** documentation reconciliation, Work Done, and governed cleanup occur only after landed identity is proven; cleanup must remain recoverable/safe and never force-delete an unmerged or dirty worktree.

## Acceptance

1. **Given** a valid persisted PromotionReady handoff, **when** `converge_change_to_done` is invoked, **then** it executes the canonical promotion stage order through `PromotionController` and returns structured execution state.
2. **Given** a persisted completed stage prefix, **when** the same operation resumes, **then** completed stages are not invoked again and their observations remain available to later stages.
3. **Given** an external mutation whose response was lost, **when** convergence resumes, **then** it re-reads authoritative state and reuses the exact existing result instead of blindly duplicating the mutation.
4. **Given** GitHub Actions are pending or failing for the exact PR head, **when** convergence reaches the CI stage, **then** merge does not occur and the resumable checkpoint identifies that exact stage/head.
5. **Given** exact-head Actions success but Work merge readiness is false, **when** convergence runs, **then** merge does not occur.
6. **Given** PromotionReady evidence, **when** all promotion stages run, **then** no KIS substantive implementation review operation is invoked.
7. **Given** a change already merged before a retry, **when** convergence resumes, **then** it continues from observed landed truth through documentation, Work completion, and eligible cleanup.
8. **Given** all terminal stages are satisfied, **when** convergence completes, **then** state is `done` and a second identical call is a no-op over the persisted completed checkpoint.

## Risks and recovery

- External GitHub/Work operations can time out after applying; recover only by exact authoritative read/reconciliation and checkpointed observations.
- A stale or changed PromotionReady handoff invalidates the checkpoint by fingerprint and fails closed.
- MCP task storage may be process-local; durable KIS promotion state must independently permit resume after reconnect or server restart.
- Recovery never weakens registered GitHub exact-head guards, Work readiness, or repository cleanup rules.

## Out of scope

- Automatic Work activation → TaskHandoff/port/evidence lifecycle (`#586`).
- ReviewClosure automation, candidate reuse/provenance/scenario selection (`#587`).
- Typed phase obligations, default PromotionReady PR lookup, schema/effect-fixture hardening (`#588`).
- MCP workflow Prompts, discovery cache hints, or header routing (`#589`).
