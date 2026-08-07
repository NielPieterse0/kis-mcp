# Change Specification: CI Governance Validation

- **Change ID**: `065-ci-governance-validation`
- **Status**: Ready
- **Risk Profile**: standard

## Outcome

Allow isolated CI governance validation without requiring unrelated local worktrees while preserving strict local topology checks.

## Authority and scope

- Authoritative sources: `scripts/change-governance.py`, Work Management workflow, exact-head run #15 failure evidence.
- Owned paths: governance implementation/tests, Work Management workflow/test, this change record.
- Shared paths: none.
- Excluded paths: none.
- Dependencies: none.
- Integration owner: none.

## Requirements

- **REQ-001**: Local governance validation must continue requiring all active worktrees.
- **REQ-002**: Isolated CI may explicitly validate claim semantics without requiring unrelated sibling worktrees.
- **REQ-003**: Work Management CI must opt into isolated claim validation explicitly.

## Acceptance

1. **Given** an active claim without its sibling worktree, **when** normal validation runs, **then** it still fails with `ACTIVE_CHANGE_WORKTREE_MISSING`.
2. **Given** the same isolated checkout, **when** `validate --claims-only` runs, **then** claim validation succeeds if semantic claims are valid.
3. Focused tests, scope validation, diff checks, and canonical verification pass.

## Risks and recovery

- Risk: accidentally weakening local worktree governance.
- Recovery: revert this change; default validation remains strict by design.

## Out of scope

- Closing or altering unrelated active changes such as 063 or 064.
- Changing P5 behavior or GitHub Project mutation settings.
