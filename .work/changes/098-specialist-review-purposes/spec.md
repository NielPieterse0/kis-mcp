# Change Specification: Specialist Review Purposes

- **Change ID**: `098-specialist-review-purposes`
- **Status**: Active
- **Risk Profile**: standard

## Outcome

Expand the existing bounded advisory reviewer with specialist architecture, performance, test-quality, documentation, and API/contracts purposes while preserving existing code-quality and safety/security behavior.

## Requirements

- **REQ-001**: `review_change_with_agent` accepts exactly seven fixed review purposes: `code-quality`, `safety-security`, `architecture`, `performance`, `test-quality`, `documentation`, and `api-contracts`.
- **REQ-002**: Each purpose changes only the review rubric; evidence collection, backend selection/fallback, output normalization, budgets, and provenance remain shared.
- **REQ-003**: Every purpose keeps the existing no-mutation, no-commit/merge, and no-nested-agent prompt boundary.
- **REQ-004**: Performance review identifies likely performance risks and missing measurements but must not invent benchmark results.
- **REQ-005**: Unknown review types fail before evidence collection/backend invocation.
- **REQ-006**: Current implementation and operator documentation list the exact supported purposes without creating new authority.

## Acceptance

1. Each new purpose produces the exact purpose-specific prompt through either configured backend.
2. Existing code-quality/safety-security behavior and model/backend semantics remain unchanged.
3. Unknown purposes remain structurally rejected before evidence collection.
4. No new tool, provider, mutation, policy, or nested-agent capability is introduced.
5. Canonical repository verification passes on the exact final head.

## Out of scope

- Executing multiple specialist reviews as one delivery workflow; that belongs to a later orchestration slice.
- New model profiles/backends or reviewer evidence sources.
- Govern findings or Work-policy decisions based on reviewer output.
