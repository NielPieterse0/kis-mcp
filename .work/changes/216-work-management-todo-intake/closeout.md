# Closeout: Work Management Todo Intake

## Implemented scope

- Added configured provider-intake aliases with current `todo -> inbox` mapping.
- Preserved compatibility for older settings that omit `intake_aliases`.
- Added fail-closed guards preventing aliases from targeting undeclared states or shadowing declared lifecycle states.
- Added end-to-end Todo-to-Ready and settings-contract regression coverage.

## Validation evidence

- Focused checks: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/work_management/test_command_plane_settings.py tests/work_management/test_command_service.py -q` -> 29 passed.
- Repository verification: canonical exact-head verification remains for PR CI.
- Diff scope check: `pwsh -File scripts/change-workflow.ps1 check` -> pass.

## Review

- Findings: initial manual review found schema/loader required-key mismatch; API-contract review then identified backward-compatibility risk from making the new key mandatory and alias-shadowing risk.
- Resolutions: made `intake_aliases` optional with empty default for compatibility; added declared-state collision guard plus unknown-alias and multiple-alias tests. One reviewer evidence projection returned an empty diff and was rejected as non-evidence. The later exact-range review's claim that the schema still required `intake_aliases` was rejected against the current schema; its useful edge-coverage recommendations were implemented. Exact final-commit review remains required before publication.

## Git and merge

- Branch: `change/216-work-management-todo-intake`
- Worktree: `.work/worktrees/216-work-management-todo-intake`
- Commit:
- Pull request or merge:
- Cleanup:

## Residual items

-
