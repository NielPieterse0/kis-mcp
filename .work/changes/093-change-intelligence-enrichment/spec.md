# Change Specification: Change Intelligence Enrichment

- **Change ID**: `093-change-intelligence-enrichment`
- **Status**: Approved by operator request
- **Development level**: Medium — cross-module Discover behavior and public request/response contracts, no Work-policy change
- **Risk Profile**: standard

## Outcome

Enrich the existing Discover planning/context/change-impact pipeline with stronger repository-pattern, blast-radius, support-surface, replacement, and planned-versus-actual evidence without adding a new scanner, impact engine, authority, evidence store, project registry, or lifecycle.

## Authority and scope

- Authoritative sources: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, `policy/kis-mcp.policy.json`, `docs/OPERATIONS.md`, `docs/DISCOVER-MODULE-PRODUCT-SPEC.md`.
- Operator input: attached next-change specification for Discover → verification/review → Work enrichment.
- Owned paths: exactly those recorded in `scope.json`.
- Shared paths: none.
- Excluded paths: `policy/**`.
- Dependencies: none; reuse current persistent project intelligence and optional Serena evidence.
- Integration owner: none; this slice must merge and clean before the next slice starts.

## Requirements

- **REQ-001 Repository patterns:** `plan_change` reports deterministic `REUSE`, `EXTEND`, `REPLACE`, or `NEW` guidance from current context/change evidence, with reasons rather than authority claims.
- **REQ-002 Support-surface impact:** impact analysis relates changed implementation to relevant documentation, configuration, contract/schema, and policy-sensitive paths using bounded deterministic evidence.
- **REQ-003 Dependency radius:** Python impact includes bounded deterministic transitive import dependants without displacing direct high-confidence evidence.
- **REQ-004 Context enrichment:** `get_code_context` retains bounded task-relevant support artifacts associated with selected implementation evidence; it remains read-only and budgeted.
- **REQ-005 Replacement evidence:** `analyze_change` identifies deleted/renamed paths that still have deterministic dependant/reference evidence as replacement/stale-code candidates; it never authorizes deletion.
- **REQ-006 Reconciliation:** `analyze_change` optionally accepts prior planned paths/fingerprint and reports unplanned/missing paths plus stale-review evidence when actual scope diverges.
- **REQ-007 Verification/test continuity:** existing affected-test and verification handoffs remain compatible and include newly discovered impact evidence where applicable.
- **REQ-008 Authority:** no new Work policy decision, runtime authorization, network execution, or process-backed analyzer is introduced.
- **REQ-009 Determinism:** identical repository state, request, settings, and provider evidence produce stable ordering/fingerprints.

## Acceptance

1. A pre-change `plan_change` returns a bounded planned path set and repository-pattern guidance while performing no Work.
2. A changed Python module exposes direct and bounded transitive dependants, relevant support surfaces, affected tests, and verification handoffs.
3. A deleted or renamed path with retained references appears as a replacement candidate; ordinary modified paths do not.
4. Supplying planned paths to `analyze_change` reports exact planned/actual/unplanned/missing sets and marks prior evidence stale only when scope diverges.
5. `get_code_context` can retain a related contract/config/document/policy artifact even when task-token scoring alone would otherwise omit it, subject to existing budgets.
6. Existing public inputs remain backward compatible; new reconciliation inputs are optional.
7. Focused tests, schema validation, scope check, canonical `scripts/verify.ps1`, and independent reviews pass on the exact final head.

## Risks and recovery

- Risk: heuristic support-surface matching can over-select weak relationships. Mitigation: label provenance/confidence, require token evidence, bound by existing budgets, and never treat results as Govern/Work authority.
- Risk: transitive dependency evidence increases output. Mitigation: reuse the existing dependant budget and lower confidence for transitive edges.
- Risk: public schema extension breaks strict consumers. Mitigation: additions are backward-compatible optional request fields and additive response fields under updated checked-in schemas/tests.
- Recovery: revert the slice merge or restore the prior immutable commit; no migration or generated-state mutation is required.

## Out of scope

- Ruff, coverage.py, Vulture, LibCST, type checker, or dependency changes (Slice 2).
- agnix execution integration (Slice 3), verification selection policy (Slice 4), executable workflow orchestration (Slice 5), commissioning/closeout automation (Slice 6), and top-level completion coordination (Slice 7).
- Govern implementation, new Work policy rules, external network calls, automatic deletion, or AgentSys orchestration authority.
