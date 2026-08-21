# GitHub Provenance Validation Implementation Plan

**Goal:** Enforce provider-verified GitHub issue/PR/head/merge identity across coordinator evidence.

**Architecture:** Treat `PlannerRequest.external_provenance` as an untrusted GitHub status claim. `WorkPacketService` resolves authoritative provider identity through an injected read-only resolver, validates the exact tuple, and freezes a versioned verified envelope. Worker/reconciliation/integration evidence carries that envelope unchanged; delivery may add the exact observed merge SHA only after validating the frozen PR/head identity.

**Tech Stack:** Python dataclasses/services, JSON Schema 2020-12, pytest/jsonschema, existing coordinator durable evidence.

## Global constraints

- Stay inside Change 217 scope.
- Preserve existing authority/fencing, exact Git verification, and Work Management semantics.
- Use tests before behavior changes.
- No generic provider or status-system redesign.

### Task 1 — Provenance contract and provider admission

- Add strict GitHub provenance tuple/envelope validation.
- Add provider-resolver boundary to packet issuance.
- Reject issue↔PR, repository, stale-head, and malformed identity mismatches.
- Tighten work-packet schema and contract fixtures.

### Task 2 — Immutable propagation and reconciliation

- Freeze verified provenance into execution/handoff identity.
- Reconcile handoff provenance against durable packet evidence.
- Surface typed provenance validation status and block rejected evidence from integration.
### Task 3 — Concurrent aggregation and integration lifecycle

- Add deterministic aggregation for exact-match concurrent claims and visible quarantine for conflicts.
- Preserve verified tuple in queue and exact-head CI evidence.
- Require delivered merge SHA to be consistent with frozen repository/issue/PR/head provenance.

### Task 4 — Verification and documentation

- Run focused coordinator tests and schema validation.
- Run governed scope check and required architecture/API-contract reviews.
- Update `SPEC.md` with the provenance authority rule.
- Prepare exact-head PR, require canonical Actions and Work Management readiness, then merge/reconcile/clean.