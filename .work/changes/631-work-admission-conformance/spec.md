# Change Specification: Work Admission Conformance

- **Change ID**: `631-work-admission-conformance`
- **Status**: Implemented; verification pending
- **Complexity**: Large
- **Risk triggers**: external_action, public_contract

## Outcome

Implement issue #542 only: one deterministic formal Work admission contract while preserving Inbox Ideas as pre-work.

## Authority and scope

- Repository authority: `AGENTS.md`, `SPEC.md`, existing Work Management machine contracts.
- Work authority: GitHub issue #542 and its inherited #382/#424/#448/#451 requirements.
- Owned/excluded paths: `scope.json`.
- Parallel #619 lifecycle-adapter and #628 task-completion paths remain excluded.

## Requirements

- Formal admission fails on missing semantic inputs instead of inventing them.
- Repository identity resolves uniquely from the registered Work project set.
- Inbox Ideas remain pre-work and are never auto-promoted into issues.
- Formal issues use deterministic body sections without duplicating Project metadata.
- `Project ID` and `Issue Number` are derived from canonical source identity.
- Done/idempotency matches remain immutable; follow-on work uses a new issue with explicit lineage.
- Apply requires an idempotency key and reconciles Project state through the existing bounded reconciliation service.

## Acceptance

1. Preview resolves a registered repository to exactly one Project ID and returns deterministic formal issue/project projections.
2. Apply creates or reuses one open idempotency match, never reopens closed history, and projects canonical issue identity.
3. `Issue Number` is a numeric GitHub-evidence field in canonical semantics, command-plane authority, and Project schema.
4. The MCP surface exposes bounded `project_management_admit_work` with preview-by-default behavior.
5. Focused tests, scope check, repository-required verification, review, CI, merge, and Work closeout pass.

## Risks and recovery

- External issue/Project mutation is apply-gated and idempotency-keyed; preview is non-mutating.
- Ambiguous repository or issue identity fails closed.
- Recovery is source/Project reconciliation through the same canonical identities; Done issues are never reopened.

## Out of scope

- #619 live record adapters and existing lifecycle command implementation.
- #628 durable task completion.
- Once-through automation/programme #584.
- Housekeeping/conformance runners outside #542's consolidated admission slice.
