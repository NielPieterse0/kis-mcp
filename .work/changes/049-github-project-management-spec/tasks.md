# Tasks: GitHub Project Management Capability

## Documentation baseline

- [x] Read repository authority and current product/provider architecture.
- [x] Read the `develop-docs` and approved `modularity-assessment` procedures.
- [x] Inspect active 047 and 048 scopes and define non-overlapping documentation ownership.
- [x] Create the isolated `049-github-project-management-spec` worktree and branch.
- [x] Register `scope.json` before editing the target specification.
- [x] Record the known external stale-claim validation limitation.
- [x] Verify current GitHub Projects, API, ruleset, and official MCP capabilities.
- [x] Define authority, records, lifecycle, fields, views, and intake.
- [x] Define specification, decision, assumption, risk, approval, hold, and traceability behavior.
- [x] Define review-run evidence, triage, extraction modes, and finding lifecycle.
- [x] Define provider-neutral module boundaries aligned with 047.
- [x] Define public workflow, provider, settings, automation, CLI, CI, and Git requirements.
- [x] Define security, consistency, migration, recovery, acceptance, and phased delivery.

## Review and verification

- [x] Review final documentation against the plan and source inventory.
- [x] Check stable IDs, headings, JSON examples, links, placeholders, and terminology.
- [x] Run `git diff --check`.
- [x] Run `pwsh -NoProfile -File scripts/change-workflow.ps1 check` and record unrelated blockers.
- [x] Run applicable documentation/repository verification and record limitations.
- [x] Commit the documentation baseline on the isolated branch.

## Future implementation

- [ ] Obtain operator approval of the target specification.
- [ ] Reconcile architecture and paths with merged change 047.
- [ ] Run a measured modularity assessment before P1.
- [ ] Create separate governed implementation changes for phases P1 through P6.
- [ ] Create and commission the GitHub Project only through an approved future slice.
- [ ] Raise, review, merge, and safely clean up change 049 when its reserved work is complete.
