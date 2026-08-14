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
