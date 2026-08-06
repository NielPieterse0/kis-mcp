# Closeout: GitHub Project Inventory

## Completed scope

P1 adds immutable provider-neutral Project inventory contracts and an asynchronous backend protocol. The GitHub adapter invokes only pinned read operations `projects_get` and `projects_list`, uses fixed methods, bounds pagination, normalizes supported response wrappers, redacts upstream errors, and exposes truncation explicitly.

The GitHub provider now advertises a separate `project_management.read` capability. Project calls are authorized only for exact configured `(owner, owner_type, project_number)` identities; repository-owner approval alone is insufficient.

## Verification

Completed on 2026-08-06:

- Focused work-management and GitHub provider tests passed.
- `scripts/change-workflow.ps1 check` passed for all changed paths.
- `scripts/verify.ps1` passed.
- Pytest completed with 909 passed and 2 skipped.
- Configuration, dependency, syntax, governance, line-ending, and exact three-rule checks passed.

## Review

The findings-first review returned broad claims without actionable evidence. Direct inspection identified and corrected the substantive scope defect: Project access is now governed by explicit Project bindings rather than inferred repository owners. Regression coverage verifies exact approved identity, invalid methods, malformed identity, and mutation rejection.

## Git and merge

- Branch: `change/051-github-project-inventory`
- Worktree: `.work/worktrees/051-github-project-inventory`
- Base: `change/049-github-project-management-spec`
- State: ready for stacked review after change 049 lands.

## Residual programme phases

- P2: intake, typed records, governance records, and holds.
- P3: implementation traceability and documentation milestones.
- P4: review evidence, triage, and finding extraction.
- P5: automation, CLI, CI, reconciliation, live commissioning, and status.

P1 performs no remote Project mutation and does not claim live GitHub Project commissioning.