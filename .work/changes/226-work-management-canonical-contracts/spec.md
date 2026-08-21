# Change Specification: Work Management Canonical Contracts

- **Change ID:** `226-work-management-canonical-contracts`
- **Status:** Approved for implementation by operator on 2026-08-21
- **Development level:** Complex
- **Repository complexity:** `large`
- **Risk triggers:** `architecture_boundary`, `migration`, `persistent_state`, `public_contract`
- **Work item:** `NielPieterse0/kis-mcp#430` / `WORK-430`

## Outcome

Establish one bounded, Work-specific machine-readable authority for Work Management field/vocabulary/applicability semantics, lifecycle/operation semantics, and selection semantics. Existing command-plane settings and the GitHub Project schema become validated projections of that authority. `project_management_contract` exposes the canonical contract through the existing MCP surface.

The change also removes misleading generic Work automation switches after recording their disposition, adds the three #419 live-verification fields to the canonical/provider projection, and preserves current approved selection behavior. It does not introduce the withdrawn #444 selection tiers.

## Authority and evidence

1. `AGENTS.md` governs repository workflow, ownership, and change isolation.
2. `SPEC.md` governs current implemented architecture.
3. #430 original issue body and its first bounded Work-contract pilot comment define the requested outcome.
4. #430 correction comment explicitly voids the later #444 tier-order assertion.
5. #419 defines `Live Verification`, `Commissioning Key`, and `Live Verification Evidence`.
6. Current machine evidence is `settings/work-management/*.json` plus the applicable Work Management source and tests.
## Current-state findings to preserve

- `command-plane.settings.json` currently duplicates field authority, lifecycle states/transitions, queue eligibility/ranking, readiness, claim, and delivery semantics.
- Python enums and lifecycle guards add overlapping semantic authority.
- `selection.py` and `project_commands.py` independently implement related eligibility/ranking logic.
- `github-project-schema.json` owns provider field/option/view shape but does not define complete operational meaning.
- `project_management_contract` currently exposes operation/result-envelope semantics only.
- `scheduled_reconciliation` is superseded by the explicit housekeeping runtime.
- `safe_repair` belongs to the housekeeping preview/receipt/apply model.
- `auto_add`, `close_sync`, `merge_sync`, and `review_extraction` are exposed settings with no named production automation.
- Live schema evidence on 2026-08-21 reports fields ready but views not ready: four unverified views and three view mismatches.

## Design decisions

### D-001 — Three Work-specific canonical contracts

Create exactly three canonical JSON contracts beneath `settings/work-management/contracts/`:

1. `work-item-semantics.json` — fields, controlled vocabulary, authority/direction, applicability, required/conditional-required rules, population/source rules, and provider representation intent.
2. `work-lifecycle-operations.json` — lifecycle states, transitions, guards, claims, readiness, completion, delivery/verification/commissioning semantics, and operation side-effect classes.
3. `work-selection.json` — eligibility, exclusions, dependency evidence, ranking, stable tie-breaking, and explanation/reason semantics.

These are Work Management artifacts, not a generic repository-wide MRD framework.
### D-002 — One canonical loader and normalized internal model

Add one Work Management loader/validator that reads the three contracts, rejects unknown or inconsistent structure, and returns immutable normalized models. Existing Work modules consume that model directly or consume a projection only after exact validation against it.

No second semantic parser may be introduced in provider or workflow code. Python enums may remain typed implementation conveniences, but tests must prove their values are an exact projection of the canonical vocabulary rather than an independent list.

### D-003 — Existing JSON becomes validated projection

`command-plane.settings.json` remains a compatibility/runtime projection, not semantic authority. Every semantic value it repeats must be mechanically derived from or validated exactly against the three canonical contracts. Operational knobs that are not semantic duplicates may remain settings-owned.

`github-project-schema.json` remains the provider-specific desired Project projection. Field names, field types, controlled options, and semantic field applicability must trace to `work-item-semantics.json`; lifecycle-related options must trace to the lifecycle contract. View layout/filter/display intent stays provider-projection data but may reference only canonical fields/options.

Projection drift is a validation failure. A projection must not silently extend canonical vocabulary.

### D-004 — MCP exposure uses the existing surface

Extend `project_management_contract` rather than adding a new generic MCP tool. Its result must include canonical contract versions/fingerprints, normalized field/vocabulary/applicability semantics, lifecycle/operation semantics, selection semantics, and the existing result-envelope/typed-error/operation-effect information.

The tool remains read-only and provider-neutral. It exposes authoritative semantics; it does not create Project fields, change work state, or execute selection.
### D-005 — Preserve current approved selection behavior

The canonical selection contract must first reproduce current approved behavior before any policy redesign:

- provider-backed candidates are open issues in configured eligible Work states (currently `Ready`);
- required Project metadata must be present and valid;
- claimed work is excluded from next-work selection;
- dependency evidence must be available and blockers must be empty;
- ranking is current configured Priority, Effort, creation order, then stable record identity;
- normalized-domain selection retains its current approval/dependency guards where applicable.

The two existing selection paths must converge on one shared canonical evaluator or one shared decision primitive with adapter-specific evidence extraction. Differential tests must prove no selection-order change for the current contract.

The withdrawn Defect → Material Finding → Unfinished/Ongoing → New Work tiers from #444/Change 223 are explicitly prohibited in this change.

### D-006 — Automation-setting disposition

The `automation` object is removed from Work Management settings rather than retained as six permanently-false pseudo-capabilities.

- `scheduled_reconciliation`: superseded; scheduling authority is `settings/housekeeping.settings.json` plus the housekeeping runtime.
- `safe_repair`: superseded; bounded repair is the housekeeping preview → receipt → supervised apply contract.
- `auto_add`: retire the generic switch; current intake/reconciliation remains explicit and idempotent, not an unnamed background auto-add service.
- `close_sync`: retire the generic switch; current completion/documentation reconciliation remains explicit evidence-gated Work operations.
- `merge_sync`: retire the generic switch; merge readiness/landing/queue workflows remain explicit governed operations.
- `review_extraction`: retire the generic switch; current review persistence/intake remains explicit, with no unapproved background extractor.

If implementation evidence proves any removed switch represented an approved capability not covered by the named mechanisms above, implementation must stop for that item and raise a bounded follow-up defect rather than silently implement it.
### D-007 — #419 live-verification fields

Add these canonical field definitions and place them as the final three managed Project fields:

- `Live Verification`: single-select with `Not Assessed`, `Not Required`, `Pending`, `Passed`, `Failed`, `Blocked`.
- `Commissioning Key`: text containing the deterministic idempotency key.
- `Live Verification Evidence`: text containing a compact evidence reference or commissioning linkage, never free-form logs.

`Verification` remains repository/source verification. `Live Verification` remains post-merge runtime proof; neither may substitute for the other.

### D-008 — View drift and live commissioning boundary

This change updates and validates the desired provider projection but does not directly mutate the live GitHub Project during implementation. Existing schema status/plan/commissioner paths remain the only schema mutation route.

Current live view drift is verification evidence, not permission to bypass the commissioner. Final live repair and runtime proof remain under #419 commissioning/backfill lineage after the repository change lands.

### D-009 — Semantic completeness without invented authority

Every governed field and controlled value must end with one operational definition. Definitions must be traced to current behavior, explicit issue/operator authority, or an approved decision recorded in this change.

When current code/config/prose exposes only a token with no sufficiently authoritative operational meaning, implementation must record it as an unresolved design decision and obtain operator approval before assigning normative meaning. Tests or common usage alone do not authorize invented semantics.

The governance-boundary audit must record each duplicated/text-only/hard-coded rule, its current location, canonical owner, migration action, and whether downstream code is generated from or validated against that owner.
## Requirements

- **REQ-001 — Canonical semantics:** the three Work-specific contracts are strict, versioned, machine-readable, internally consistent, and the sole normative owners for their declared semantics.
- **REQ-002 — Complete vocabulary:** every managed field and every governed enumeration value has an operational definition, authority/direction, and applicable source/population rules.
- **REQ-003 — Applicability:** unconditional, conditional, and non-applicable field rules are explicit and machine-testable; unmet mandatory conditions fail closed where they gate an operation.
- **REQ-004 — Lifecycle/operations:** state transitions, readiness, claims, release/hold/defer/complete guards, delivery stages, verification distinctions, and operation effects are canonical and deterministic.
- **REQ-005 — Selection:** both selection implementations consume the same canonical selection decision model and preserve approved current ordering and exclusion behavior.
- **REQ-006 — Projection integrity:** command-plane settings, Python enum/value sets, and GitHub Project field/options are generated from or exact-validated against canonical semantics.
- **REQ-007 — MCP contract:** `project_management_contract` exposes canonical semantics plus version/fingerprint evidence using the existing read-only tool.
- **REQ-008 — Automation cleanup:** the six generic automation switches are removed after the D-006 dispositions are verified; no dormant capability is advertised.
- **REQ-009 — Live verification projection:** the three #419 fields are canonical, distinct from source `Verification`, and projected as the final managed Project fields.
- **REQ-010 — Governance audit:** every rule affecting agent decisions, authority, admissibility, state, execution, or evidence has one bounded owner or a separately tracked unresolved defect/decision.
- **REQ-011 — No dual prose authority:** `SPEC.md` and operator documentation describe ownership/current behavior and link to machine authority; they do not redefine enumerations or decision rules.
- **REQ-012 — Compatibility/recovery:** migration is fail-closed, existing Project data is not destructively rewritten, and live provider repair remains explicit/idempotent through the registered commissioner.

## Acceptance scenarios

1. Mutating a projection token without changing its canonical owner causes deterministic validation failure.
2. Mutating a Python enum/value set away from canonical vocabulary is caught by conformance tests.
3. Both selection adapters return equivalent decisions/reasons for equivalent evidence under the current approved policy.
4. A test fixture implementing the withdrawn #444 tier order fails because no such tier exists in the canonical contract.5. The six obsolete automation keys are absent from accepted Work settings and from the exposed contract; named replacement mechanisms remain independently testable.
6. `Live Verification`, `Commissioning Key`, and `Live Verification Evidence` validate as the final three Project fields with #419-prescribed representations/options.
7. `project_management_contract` returns the canonical semantic sections and stable fingerprints without provider mutation.
8. Schema status continues to report live view drift until the approved commissioner repairs it; repository tests do not fabricate live readiness.
9. A complete governance-boundary audit has no unresolved duplicated normative rule; any genuine missing capability or semantic decision is separately bounded before closeout.
10. Focused positive, negative, drift, round-trip/conformance, and current-policy regression tests pass on the implementation head.

## Risks and recovery

- **Semantic migration drift:** strict projection comparison and differential behavior tests prevent silent meaning changes. Recovery is revert to the last valid contract/projection set.
- **Provider schema drift:** no direct deletion/recreate path is added. Recovery uses the existing registered commissioner and provider history; incompatible live types remain explicit blockers.
- **Runtime compatibility:** retain current MCP/FastMCP tool registration and extend only the structured result payload. Contract loading fails closed on incompatible files.
- **Selection regression:** freeze current policy with before/after fixtures and reason-level comparison before consolidation.
- **Over-generalization:** keep loaders/types under Work Management; do not create a generic MRD engine or repository-wide schema framework.
- **Unresolved vocabulary meaning:** do not infer. Record the missing authority and obtain an explicit decision before implementing that normative entry.

## Out of scope

- Any #444/Change 223 work-class or priority-tier policy.
- A generic MRD framework, schema language, generator platform, or migration of unrelated KIS modules.
- New unattended background automation for auto-add, close, merge, or review extraction.
- The #419 commissioning classifier/runner, backfill execution, or live-runtime restart logic.
- Direct ad-hoc GitHub Project mutation or manual repair outside the registered commissioner.
- Changes to HR-001/HR-002/HR-003 or repository/Git landing authority.

## Approval gate

This is a Complex change. Human approval of this specification and the accompanying implementation plan is required before any production/configuration/test implementation begins. Approval of the issue or prior exploratory discussion is not equivalent to approval of this written design.