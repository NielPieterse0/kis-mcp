# Change: Project Selector Field Drift

- **Change ID**: `146-project-selector-field-drift`
- **Development level**: Small

## Outcome

Keep Work Management board/selector reads available when the shared GitHub Project has not yet provisioned all command-plane fields.

## Scope and acceptance

- Reproduce issue #235 through the live `field_not_found` provider response.
- Recover only from typed `field_not_found` responses that include a valid provider candidate field set.
- Retry `list_project_items` with the intersection of requested names and provider-declared candidates.
- Preserve strict failure for malformed/missing item collections and unrelated provider errors.
- Cover the adapter path plus board/selector behavior with focused regression tests.

## Implementation and verification

- The GitHub Project adapter now recognizes only the typed `field_not_found` provider response, intersects requested fields with provider-declared candidates, and retries the same page once.
- Any unreconciled or repeated `field_not_found` fails closed with a typed inventory error.
- Pagination recovery preserves the active cursor and continues normally after the bounded retry.
- Focused verification: 35 tests passed across adapter, enhanced board tools, board selection, and GitHub Project management coverage.
- Python compilation, `git diff --check`, and `change-workflow check` passed.
- Ruff was unavailable in the locked environment and was not installed ad hoc.
- Independent Codex code-quality re-review completed with zero findings after the initial fail-closed/pagination findings were resolved.
- The composed `execute_change_workflow` attempt returned a transient upstream 502 before producing evidence; direct bounded verification was used instead.

## Local governance limitation

Canonical `change-workflow new/validate` is currently blocked by unrelated active-claim conflicts involving changes 140, 142, and 145. This worktree was created under the documented emergency manual-worktree exception from exact synchronized `main`; its own `change-workflow check` passes, while the unrelated global conflict is recorded rather than treated as a pass.
