# Specification

## What are we changing?
Promote bounded Agnix diagnostics from `validate_agent_configuration` into additive MCP 2026 quality evidence with stable categories, baseline/app-specific scope, and lifecycle reuse stages.

## Why?
Issue #568 requires reusable evidence across discovery, scaffolding, execution, completion, and review instead of raw validator output that consumers must reinterpret independently.

## Intended outcome
Future Agnix runs can distinguish MCP-baseline findings from app-specific findings and route them to the relevant KIS lifecycle stages without introducing a second validator.

## In scope
- Normalize the seven MCP 2026 concern categories required by #568.
- Preserve the original bounded diagnostic in each evidence item.
- Add the normalized evidence to the existing validation response.
- Record the adoption matrix and exemplar-source limitation.

## Out of scope
- Editing exemplar applications.
- Changing Agnix installation/version/runtime behavior.
- Once-through or Work Management changes owned by parallel agents.

## Validation
Focused agent-validation tests, contract regression tests, independent review, and repository acceptance checks.

## Rollout / rollback
Additive response field only. Roll back by reverting this change; the existing raw `diagnostics` contract remains intact.
