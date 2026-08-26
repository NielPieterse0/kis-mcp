# Change Specification: Resource Link Large Results

- **Change ID**: `245-resource-link-large-results`
- **Status**: Implementing
- **Development level**: Medium
- **Documentation level**: Medium

## Outcome

Offload oversized capability-dispatch results into bounded KIS-owned MCP resources while preserving a useful summary and exact retrievable evidence.

## Authority and scope

- Authority: `AGENTS.md`, `SPEC.md`, #476, MCP 2026 resource/tool/schema corpus referenced by #476.
- Runtime boundary: existing `execute_read_action`, `execute_change_action`, and `execute_external_action` result-budget layer only.
- Storage authority: generated KIS state root; repository and provider source authority remain unchanged.

## Requirements

- **REQ-001**: Oversized successful structured dispatcher results return a bounded summary plus an MCP `ResourceLink` to exact canonical JSON.
- **REQ-002**: Each successful offload gets an opaque random per-dispatch grant URI; the exact payload carries an independent SHA-256 integrity identity and the stored envelope records the originating operation.
- **REQ-003**: Readability is bounded by configured TTL, maximum active entries, and per-resource bytes. Expired generated entries are moved through the existing recoverable quarantine lifecycle during later store maintenance; resource reads themselves never delete state.
- **REQ-004**: Small results, eligibility, approval, middleware, provenance, and Work authority remain unchanged. Under the repository's single-operator supervised trust model, possession of the unguessable returned grant is the bounded read authority for that one already-authorized result; grants are never deduplicated across dispatches.
- **REQ-005**: If a result cannot be persisted within the resource byte/entry bound, preserve the existing explicit `RESULT_BUDGET_EXCEEDED` summary without a false resource claim.

## Acceptance

1. An oversized dispatcher call returns a useful bounded summary and one `resource_link` content block.
2. Reading the linked resource returns the complete structured result and matches its SHA-256 identity.
3. Focused settings/execution/gateway tests pass; governance and required reviews are clean.

## Risks and recovery

- Persistent generated state is bounded and non-authoritative. Expired active entries leave the store only through recoverable quarantine; no ordinary read permanently deletes evidence.
- No provider call is replayed during resource retrieval.

## Out of scope

- Changing provider-native result contracts, adding new authorization, or making resource state durable Work authority.
