# Tasks: Multi-Project Work Management Foundation

## Programme authority

- [x] Move the working specification from `docs/development` into `.work/programmes/work-management`.
- [x] Generalize the capability for multiple managed repositories and backend bindings.
- [x] Add configurable pre-merge and post-merge documentation milestones.
- [x] Add programme control, roadmap, modularity evidence, and ADR-001.
- [x] Update the change scope to own only the programme workspace and P0 domain package.

## P0 implementation

- [x] Write failing project and record contract tests.
- [x] Implement immutable provider-neutral contracts and package exports.
- [x] Run focused contract tests and repository verification.
- [x] Write failing lifecycle and documentation milestone tests.
- [x] Implement deterministic lifecycle validation.
- [x] Run focused lifecycle tests and repository verification.
- [x] Write failing next-work selection tests.
- [x] Implement deterministic project-filtered selection and explanations.
- [x] Run focused selection tests and repository verification.
- [x] Add and pass provider-neutral architecture tests.
- [x] Correct provider-specific identity assumptions found in review.
- [x] Correct unreachable supersession and cross-project dependency defects found in review.

## Review and verification

- [x] Review the complete diff against the specification, plan, ADR, and modularity assessment.
- [x] Run `git diff --check`.
- [x] Run `pwsh -NoProfile -File scripts/change-workflow.ps1 check`.
- [x] Run `pwsh -NoProfile -File scripts/verify.ps1`.
- [x] Commit each logical P0 change unit without bypassing hooks.
- [x] Record current closeout evidence and residual programme phases.

## Later phases

- [ ] Reconcile platform entry points after 047 merges.
- [ ] Implement read-only GitHub Project inventory and adapter contracts.
- [ ] Implement mutation workflows, review evidence, traceability, CLI, CI, and reconciliation in separate governed slices.
- [ ] Update reader-facing repository documentation at the configured integration milestone.
