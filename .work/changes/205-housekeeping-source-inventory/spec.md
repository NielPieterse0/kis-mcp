# Change Specification: Housekeeping Source Inventory

- **Change ID**: `205-housekeeping-source-inventory`
- **Status**: Active
- **Complexity**: medium
- **Risk trigger**: `external_action`

## Outcome

Make housekeeping source-evidence collection scale with repository history by using complete bounded open-source inventories and per-run dependency caching while preserving fail-closed semantics and legacy record interpretation.

## Authority and scope

- Authorities: `AGENTS.md`, Change 194 / #364, Hold #379, Change 199 operationalization contract, and current housekeeping/provider contracts.
- Owned: `src/kis_mcp/housekeeping/work_management.py`, focused housekeeping tests, and this change record.
- Excluded: scheduler cadence/host, Work Management lifecycle repair, historical metadata normalization, source-binding cleanup, Change 195, and unrelated repository residue.
- Dependency: current merged `main` `ac7c97e8b6e874cbc775ddc77214841faa3eb07e`; live `kis-op` scheduler is already active.

## Requirements

- **REQ-205-01**: Reconciliation may treat absence from an authoritative open-issue inventory as non-open only when the provider proves the full cursor sequence complete within the configured external-read budget.
- **REQ-205-02**: If bulk evidence is unavailable, malformed, truncated, or budget-exhausted, fall back to exact source reads and retain existing fail-closed `source_evidence_incomplete` behavior.
- **REQ-205-03**: Do not reinterpret or normalize legacy Work Management status, metadata, dependency text, or historical change projections.
- **REQ-205-04**: Cache successful exact dependency states only within one backlog-readiness run; provider failures remain failures and are never cached as authority.
- **REQ-205-05**: Non-issue governed source kinds retain exact-read behavior unless a separately proven complete inventory contract exists.

## Acceptance

1. Many historical closed issue bindings plus one open missing binding complete within one authoritative complete open-issue inventory read and capture only the open source.
2. Repeated exact dependency references consume one successful source read per unique dependency within a run.
3. Incomplete/unavailable provider evidence still produces `complete=false`, suppresses apply, and records source evidence failure.
4. Existing ambiguous legacy `Blocked By` handling, lifecycle drift reporting, duplicate-binding reporting, and preview/apply authority remain unchanged.

## Risks and recovery

- Risk: treating an incomplete open-source listing as authoritative could hide live work. Control: completeness requires cursor termination; otherwise exact-read fallback/fail-closed semantics apply.
- Recovery: revert this bounded source-acquisition optimization; no Work Management mutation schema or persisted authoritative state changes.

## Out of scope

- Repairing historical Work Management records, duplicate source bindings, stale claims, missing metadata, old worktrees/branches/PRs, or Change 195 retirement work.