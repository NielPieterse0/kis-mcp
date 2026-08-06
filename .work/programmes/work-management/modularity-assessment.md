# Work Management Modularity Assessment

## Conclusions and risks

- FACT `src/kis_mcp/providers` has measured fan-in 10 and fan-out 9 in the active 047 worktree.
- FACT `src/kis_mcp/workflows` is smaller and already depends on provider and capability composition boundaries.
- REC Create a separate provider-neutral `work_management` domain package rather than extending Providers, Workflows, or Capabilities with domain state.
- REC Keep GitHub identities, pagination, scopes, and response layouts behind a later GitHub adapter.
- REC Defer gateway and workflow registration until 047 merges.
- RISK A catch-all domain package would accumulate records, provider translation, workflow orchestration, and automation in one change reason.
- RISK Premature record-type subpackages would create micro-module sprawl before measured change evidence exists.

## Scope and evidence

- Subject class: proposed package and integration seams.
- Horizon: active 047 worktree, preceding 90 days.
- Mode: measured collector evidence for existing units; declared evidence for proposed units.
- Sampling: Providers, Workflows, Capabilities, Tools, and Discover.
- Evidence strength: fan and churn evidence measured; proposed-unit churn, RFC clusters, and agent read-set remain unmeasured.

The collector output is retained in `modularity-baseline.md`.

## Proposed units

| Unit | Evidence | Outcome | Interface | Decision |
|---|---|---|---|---|
| `U-01 work_management` | D | Provider-neutral project identity, records, lifecycle, documentation milestones, and selection | Immutable contracts and pure functions | Create |
| `U-02 github work adapter` | D | Translate GitHub Project and issue operations | Port implemented against U-01 contracts | Defer until P1 |
| `U-03 work-management workflows` | D | Compose intake, review, delivery, and reconciliation tasks | Workflow descriptors and service ports | Defer until 047 merges |
| `U-04 automation assets` | D | CLI, CI, schema, and scheduled reconciliation | Versioned settings and structured results | Defer until domain and adapter stabilize |

## P0 task boundary

P0 changes only `src/kis_mcp/work_management/**` and `tests/work_management/**`. It MUST remain independent of FastMCP, Providers, Workflows, gateway composition, GitHub response layouts, and repository-global mutable state.

The P0 package SHOULD begin with no more than four production files: contracts, lifecycle, selection, and package exports. Service, settings, adapter, and workflow surfaces require later independently tested change units.

## Open evidence

- O-01: RFC kinds for the new domain are unmeasured until multiple implementation slices exist.
- O-02: Agent read-set and isolated test cost remain unmeasured until P0 is implemented.
- O-03: Public-surface coupling remains unmeasured until 047 integration begins.

No Modularity Assessment Score is claimed because proposed-unit BLR, RFC, and AGT evidence is incomplete.
