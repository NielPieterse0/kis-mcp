# Change: Project Created Field Read

- **Change ID**: `148-project-created-field-read`
- **Development level**: Small

## Outcome

Keep Work Management current/resume and board reads available when a configured field is not exposed as an item-readable GitHub Project field.

## Scope and acceptance

- Reproduce issue #243 through the live `Created` item-field request.
- Treat `list_project_fields` as the authoritative set of names eligible for `list_project_items.field_names`.
- Omit unavailable requested names before item retrieval so optional board evidence degrades to missing rather than aborting the read.
- Preserve change 146's bounded typed `field_not_found` retry for drift between field discovery and item retrieval.
- Preserve strict failure for malformed and genuinely unreconciled provider responses.
- Cover the adapter request plus current-work behavior with focused tests.

## Current evidence

- `project_management_current_work` fails identically on `kis-dev` and `kis-op` with `result text was not JSON`.
- Raw `github_projects_list` with `field_names=["Created"]` resolves field id `377123166`, then returns GitHub HTTP 400 as plain provider error text.
- `list_project_fields` does not expose `Created`; it exposes ten current fields including `Status` and `Repository`.

## Governance limitation

Canonical `change-workflow new` is blocked by the unrelated pre-existing exclusive-path collision between active changes 140 and 145. This worktree uses the documented emergency manual-worktree exception from exact synchronized `main`; the limitation is recorded rather than treated as a pass.

## Implementation and verification

- `read_inventory` now canonicalizes requested item-field names against the authoritative `list_project_fields` result before calling `list_project_items`.
- Unavailable names such as live `Created` are omitted; available names preserve provider-canonical spelling and request order.
- Change 146's typed `field_not_found` retry remains intact for drift that occurs after field discovery.
- Adapter and enhanced-tool regressions prove unavailable fields do not abort board/current-work reads and that the current Active claim remains selectable.
- Affected verification: 222 tests passed across GitHub Projects provider, Project Management workflows, and Work Management suites.
- Focused verification: 25 tests passed across adapter, enhanced tools, and board selection.
- `git diff --check` and `change-workflow check` passed.
- Ruff is unavailable in the locked environment and was not installed ad hoc.
- Earlier Codex/NVIDIA advisory attempts failed before findings; the final NVIDIA code-quality review completed successfully with no findings after the affected tests were green.
