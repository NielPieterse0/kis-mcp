# Project Tasks Improvement Programme

This document records the additive runtime and Work Management contracts introduced by governed change `140-project-tasks-improvement-programme` / programme issue #215. It complements `SPEC.md` and `docs/OPERATIONS.md`; those files remain authoritative for the platform baseline, closed Work policy, provider model, and general startup procedures.

## Authority model

The programme does not introduce a new Work authority or task store.

- Repository `.work` evidence remains authoritative for governed change scope and delivery evidence.
- Git and GitHub remain authoritative for repository, branch, pull-request, and exact-head CI state.
- The configured Work Management backend remains authoritative for Project inventory, lifecycle fields, execution ownership, and provider-native Project revisions.
- KIS runtime state is derived operational evidence. A stale lifecycle marker cannot override live process, repository, configuration, or initialization evidence.
- Control Center consumes a derived read-only Work board projection. The projection is process-local, disposable, and never a persistence authority.
- TaskPlanner is planning guidance only. No `.tasks`, `WORK_LOG`, or other duplicate durable Work truth is introduced.

Exactly HR-001, HR-002, and HR-003 remain the closed Work enforcement set.

## Runtime generation identity

Remote runtime readiness is accepted only when the currently serving process and the published lifecycle state agree.

The process captures its source revision and hashes the relevant checked-in runtime/configuration generation at startup. The generation includes the core KIS settings, registered projects, capability settings, Work Management command-plane/backend/schema settings, and the three-rule policy declaration.

A `current.json` marker is not sufficient on its own. Runtime evidence validates:

1. the requested runtime instance exists and matches the marker;
2. lifecycle is `ready`;
3. endpoint matches the configured instance endpoint;
4. the marker listener PID is the current serving PID;
5. the live Git revision and configuration generation still match the serving process generation;
6. `run_id` is syntactically bounded and safe;
7. the startup evidence path is exactly the canonical `startup-state-<run_id>.json` file for that runtime directory;
8. startup evidence reports `health=ready`, the same instance/endpoint/PID, and the current policy fingerprint.

The startup evidence file is written only after the launcher has completed its MCP initialize/readiness probe and endpoint verification. The launcher then atomically publishes the matching startup-evidence path in `current.json`.

Typed not-ready evidence includes schema, lifecycle, instance, endpoint, process, source/config generation, run identity, startup-evidence path, startup-evidence availability, and startup-evidence content mismatches. A mismatch never upgrades `remote_mcp` to external-tunnel-ready.

No credential or secret value is added to runtime evidence.

## Current/resume work

`project_management_current_work` is a read-only external Work Management operation for resuming an already claimed Active item.

Inputs:

- `project_id`
- `execution_owner`
- optional bounded `item_limit`

The operation reads the authoritative Project inventory and selects only issues whose Work State is Active and whose Execution Owner exactly matches the requested owner.

Outcomes are deterministic:

- `none`: no matching Active claim; bounded next actions point to next-work/take-next-work.
- `current`: exactly one matching Active claim; source identity, Work metadata, change ID when present, and bounded next actions are returned.
- `ambiguous`: more than one matching Active claim; no item is guessed or selected.
- `incomplete`: inventory is truncated; no item is guessed or selected.

The operation never reacquires, rewrites, or releases the claim.

## Normalized Work board

`project_management_board_data` exposes one normalized read-only projection over authoritative Project inventory.

The default view is active-first: terminal/deferred cards are omitted unless history is explicitly requested, while observed state counts still describe the complete bounded inventory page. Filters support Work State, Execution Owner, and a bounded text query; grouping supports state, owner, or repository.

Each card may expose, when available:

- project ID and Project item ID;
- repository and issue number;
- title and source issue state;
- normalized Work State and Execution Owner;
- priority and effort;
- record type and change ID;
- delivery stage and verification state;
- blocker evidence;
- complexity and risk triggers;
- authority revision and source URL.

The board also reports:

- observation timestamp;
- authority label;
- completeness/truncation and next cursor;
- state counts and grouping membership;
- next eligible item ID using the existing readiness/priority/effort/created ordering contract.

The board reads all fields required by existing next-work readiness selection so its `next_eligible_item_id` is computed from the same semantics rather than a parallel queue implementation.

## Control Center projection

A successful authoritative board read publishes the exact normalized board snapshot to a process-local `WorkBoardProjectionBridge`.

Control Center provider composition injects the latest bridge value into the `ControlCenterSnapshot.work_board` field. Control Center does not query GitHub independently, reinterpret Project fields, or persist a mirror. If no authoritative board read has occurred in the process, the field explicitly reports `status=unavailable` with reason `no_authoritative_board_read_observed_in_process`.

This is a read-only derived UX surface, not a source of lifecycle or ownership decisions.

## Result and error contract

New operational reads use an additive result envelope:

```text
schema_version
observed_at
resolved_target
provenance
  authority
  complete
  truncated
  warnings
result
next_actions
```

Existing legacy success payloads remain backward compatible. The envelope is introduced on the new current-work and board reads rather than silently replacing established response shapes.

Typed Work Management failures distinguish:

- `provider_unavailable`
- `project_not_commissioned`
- `inventory_incomplete`
- `conflict`
- `invalid_transition`
- `not_found`
- `invalid_request`
- `internal`

Typed errors retain the operation, original error type/reason, retryability, and Work Management authority label.

## MCP effect annotations

Project Management tools now describe effect scope explicitly.

External read-only operations:

- `project_management_inventory`
- `project_management_next_work`
- `project_management_current_work`
- `project_management_board_data`
- `project_management_schema_plan`
- `project_management_schema_status`

Local read-only computations:

- `project_management_merge_readiness`
- `project_management_documentation_reconcile`
- `project_management_portfolio_status`
- `project_management_verify_traceability`
- `project_management_contract`

External preview/idempotent mutation operations:

- `project_management_reconcile`
- `project_management_take_next_work`
- `project_management_claim_work`
- `project_management_release_work`
- `project_management_transition_work`
- `project_management_hold_work`
- `project_management_defer_work`
- `project_management_sync_change_classification`
- `project_management_complete_work`

Local idempotent evidence persistence:

- `project_management_persist_review`

Read-only operations set `readOnlyHint=true` and `destructiveHint=false`. Provider-backed reads use `openWorldHint=true`; pure local computations use `openWorldHint=false`. Project mutations remain non-destructive at the MCP annotation level and preserve their existing explicit `apply`/idempotency-key requirements. Review evidence persistence remains local and non-destructive.

`project_management_contract` returns the current effect classification, staged envelope contract, typed error vocabulary, and mutation rule as machine-readable guidance.

## Verification and commissioning

Pre-merge completion requires:

1. focused runtime, board/current-work, tool-contract, architecture, and Control Center tests;
2. canonical repository verification on the exact pull-request head after reconciliation with current `main`;
3. code-quality, architecture, and API-contract review with blocking findings corrected;
4. governed documentation and closeout evidence reconciled to the exact reviewed head.

Post-merge commissioning requires a KIS-enabled host to restart the relevant `kis-dev` / `kis-op` runtime generation and prove:

- MCP initialize succeeds on the restarted runtime;
- runtime evidence reports `ready` for the new source/config generation;
- `project_management_current_work`, `project_management_board_data`, and `project_management_contract` are discoverable and read-only as specified;
- a bounded Work board read publishes the same normalized payload consumed by Control Center;
- stale generation evidence is not reported as ready.

If the host cannot invoke KIS developer MCPs, repository delivery may be merged only with exact-head CI evidence, but live commissioning remains explicitly pending and the parent programme must not be falsely marked complete.
