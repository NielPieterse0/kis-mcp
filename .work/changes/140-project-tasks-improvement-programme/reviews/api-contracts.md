# API-contract review — change 140

- Review type: `api-contracts`
- Implementation reviewed through integrated code head: `55ade2511eff36cfa94e74a923bcb585d8cf5a4f`
- Result: **PASS after corrections**

## Findings and disposition

1. **Provider-backed reads were initially annotated `openWorldHint=false`.** Effect scope was corrected: external Project reads are read-only/idempotent/non-destructive with `openWorldHint=true`; pure local computations use `openWorldHint=false`. **Resolved.**
2. **The first contract descriptor omitted several established Project Management operations.** It now classifies every legacy/new operation as external read, local read, preview/idempotent external mutation, or local idempotent persistence. **Resolved.**
3. **Runtime startup evidence path was initially trusted from `current.json`.** The reader now validates bounded `run_id`, derives the canonical `startup-state-<run_id>.json` path, and rejects pointer mismatch before reading. **Resolved.**
4. **Backward compatibility:** established successful Project Management response shapes are unchanged. The provenance/result envelope is additive on the new current-work and board reads rather than replacing legacy payloads. **Confirmed.**
5. **Mutation authority:** existing `apply` and idempotency-key requirements remain explicit. No read operation acquires mutation authority and no MCP annotation marks a mutation read-only. **Confirmed.**
6. **Typed failures:** provider unavailable, uncommissioned project, incomplete inventory, conflict, invalid transition, not found, invalid request, and internal failure remain distinguishable in machine-readable errors. **Confirmed.**

## Public-contract additions

- `project_management_current_work`
- `project_management_board_data`
- `project_management_contract`
- `ControlCenterSnapshot.work_board`
- typed runtime evidence status for stale/mismatched remote readiness

All additions are bounded and additive; removal or destructive provider authority is not introduced.
