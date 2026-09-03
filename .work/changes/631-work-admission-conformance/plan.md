# Work Admission Conformance Implementation Plan

**Goal:** Complete issue #542 without entering #568/#584 or active #619/#628 paths.

**Architecture:** Add a dedicated admission module and machine contract, expose it through the existing Work Management platform mount, and reuse the existing registry-backed settings plus reconciliation service rather than modifying lifecycle adapters.

**Tech stack:** Python 3.13, FastMCP, JSON/JSON Schema, pytest, existing KIS change workflow.

## Constraints

- Stay inside `scope.json`.
- Preserve Inbox Ideas as pre-work.
- Fail closed on missing or ambiguous semantic/registry/source identity.
- Preserve Done history; follow-ons create new issues with lineage.
- Keep Project metadata out of issue bodies.
- Do not modify #619-owned parsing/tools/tests or #628-owned completion/SPEC paths.

## Execution

1. Add failing admission tests for pre-work, conformance, identity, lineage, idempotency, and ambiguity.
2. Implement pure admission behavior and deterministic issue-body/project-field projections.
3. Add bounded MCP registration and platform provider bridge.
4. Add `Issue Number` to canonical semantics, authority projection, and Project schema.
5. Run focused tests and scope validation; fix all findings.
6. Run review and canonical publication/CI/merge/Work closeout gates.
