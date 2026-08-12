# Change Specification: Governance Authority Drift Core

- **Change ID**: `100-governance-authority-drift`
- **Status**: Closed
- **Risk Profile**: standard

## Outcome

Implement a bounded deterministic Govern evaluator for repository authority and documentation drift, with the approved four read-only tool contracts available for later gateway composition.

## Requirements

- **REQ-001**: Parse repository authority order and documentation ownership from `AGENTS.md` evidence without inventing authority.
- **REQ-002**: Evaluate six fixed advisory rules: authority order, documentation ownership, owner-reference integrity, conflicting owners, exact long-form duplicate facts, and current-implementation drift.
- **REQ-003**: Reuse Discover `ReadAuthority` for bounded safe document reads; Govern evaluates evidence and does not create a second repository scanner.
- **REQ-004**: Current-implementation drift runs only when Discover-derived implementation identifiers are supplied; otherwise report an explicit unknown.
- **REQ-005**: All Govern findings are advisory (`owning_plane=govern`, `policy_effect=advisory_only`) and cannot become HR-001/002/003 decisions.
- **REQ-006**: Configuration, limits, and enabled rule set are strict JSON with a matching schema.
- **REQ-007**: Define the approved initial read-only surface: list capabilities, inspect governance, evaluate selected rules, and describe a finding.

## Acceptance

1. Missing/invalid authority structure produces deterministic findings with evidence and remediation.
2. Conflicting canonical owners and missing owner references are detected without mutation.
3. Exact duplicate long-form facts are advisory warnings, not automatic enforcement.
4. Stale current-operation claims require supplied implementation evidence; lack of that evidence remains an unknown.
5. Live core evaluation against this repo yields bounded deterministic output without policy effects.
6. Focused tests and canonical repository verification pass.

## Out of scope

- Gateway/catalogue mounting while change 099 owns the shared registration contract.
- Semantic contradiction inference or automatic documentation rewriting.
- Any Work blocking, approval, or mutation authority.
