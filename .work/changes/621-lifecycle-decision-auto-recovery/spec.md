# Change Specification: Lifecycle Decision Auto Recovery

- **Change ID**: `621-lifecycle-decision-auto-recovery`
- **Status**: Active
- **Complexity**: large
- **Risk triggers**: architecture_boundary, deployment, persistent_state

## Outcome

Expose one read-only lifecycle decision derived from existing PromotionReady/evidence/controller state, guard redundant local canonical verification, and make expected-running `kis-dev`/`kis-op` recovery automatic through an instance-scoped local-shell recovery hook.

## Authority and scope

- Authority: `AGENTS.md`, applicable `SPEC.md`, `docs/OPERATIONS.md`, `docs/operations/chatgpt-remote.md`, and existing once-through/runtime contracts.
- Existing PromotionReady, evidence validity, merge readiness, commissioning, and terminal audit remain authoritative; no second lifecycle state store is introduced.
- Recovery reuses `start-chatgpt.ps1` ownership/preflight logic and remains instance-scoped.
- Change is bound to Work `WORK-650` / GitHub issue #650.

## Requirements

- **REQ-001**: Derive `change-lifecycle-decision-v1` with exact source SHA/tree, obligation/evidence state, canonical evidence owners, one normal successor, lifecycle blockage, and bounded operation dispositions.
- **REQ-002**: At valid PromotionReady for the unchanged source/tree, classify local canonical full verification as redundant and project `converge_change_to_done` from the existing promotion controller/checkpoint as the required successor.
- **REQ-003**: A redundant/diagnostic verifier failure must not become a lifecycle blocker; return the valid controller-backed successor.
- **REQ-004**: Generalize independent local-shell recovery for `kis-dev` and `kis-op`, preserving peer isolation, local MCP readiness, tunnel readiness, idempotence, and durable recovery evidence.
- **REQ-005**: Health/recovery hooks must automatically invoke the selected instance recovery when that expected-running instance is unhealthy, without requiring the failed MCP server itself.
- **REQ-006**: Post-land development refresh must delegate to the canonical recovery primitive rather than a parallel launcher path.

## Acceptance

1. A #621-equivalent PromotionReady replay advances directly to the existing promotion controller with no redundant local full verification.
2. Evidence changes invalidate only affected evidence and controller checkpoint progress is projected without introducing another lifecycle authority.
3. Both runtime instances recover through the same generalized contract and never stop/reclaim the peer.
4. Recovery and prevented redundant work are observable in typed receipts/telemetry.
5. Existing exact-head GitHub Actions, merge readiness, commissioning, completion, and terminal audit semantics are unchanged.

## Out of scope

- A second promotion/merge state machine or lifecycle truth store.
- Moving canonical PR/merge full verification away from exact-head GitHub Actions.
- Cross-instance process ownership or failover.
