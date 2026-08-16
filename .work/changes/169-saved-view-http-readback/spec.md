# Change Specification: Saved View HTTP Readback

- **Change ID**: `169-saved-view-http-readback`
- **Status**: Active
- **Development level**: Medium

## Outcome

Restore truthful behavioral verification for broad canonical Work Management views after backlog catch-up without weakening fail-closed saved-view evidence.

## Authority and scope

- Source defect: `kis-mcp#304`.
- Runtime evidence: views `02 Programme Table` and `03 Delivery Board` are structurally matched but `unverified:malformed_http`; the registered commissioner fails on the same condition.
- Owned implementation: `src/kis_mcp/providers/github/projects/schema_commissioning.py` and its focused tests only.

## Requirements

- **REQ-001**: Accept a legitimate body-only JSON list from the saved-view items read only when completeness can be proven from the bounded page size.
- **REQ-002**: A body-only page with `len(items) >= per_page` must remain unverified because pagination cannot be proven without headers.
- **REQ-003**: Existing HTTP-envelope parsing, Link cursor validation, page/cycle limits, field-shape validation, and semantic mismatch detection remain fail closed.
- **REQ-004**: No Project schema/view mutation semantics, deletion behavior, authentication, or Work policy changes.

## Acceptance

1. A focused regression fails before implementation for a non-empty body-only page smaller than the page bound.
2. Empty, malformed, full body-only, malformed-header, pagination, and contradictory-field cases remain unverified or mismatched as appropriate.
3. Affected tests and governed scope checks pass; reviews have zero blocking findings.
4. Exact-head CI passes, merge lands, fresh runtime verifies all 12 views and returns an empty schema plan.

## Recovery and exclusions

- Recovery is ordinary PR rollback; no persistent data migration is introduced.
- Backlog lifecycle decisions and documentation-only change 168 are out of scope.