# Tasks: Multi-Project Work Management Foundation

## Programme authority

- [x] Move the working specification from `docs/development` into `.work/programmes/work-management`.
- [x] Generalize the capability for multiple managed repositories and backend bindings.
- [x] Add configurable pre-merge and post-merge documentation milestones.
- [x] Add programme control, roadmap, modularity evidence, and ADR-001.
- [x] Update the change scope to own only the programme workspace and P0 domain package.

## P0 implementation

- [ ] Write failing project and record contract tests.
- [ ] Implement immutable provider-neutral contracts and package exports.
- [ ] Run focused contract tests and fast verification.
- [ ] Write failing lifecycle and documentation milestone tests.
- [ ] Implement deterministic lifecycle validation.
- [ ] Run focused lifecycle tests and fast verification.
- [ ] Write failing next-work selection tests.
- [ ] Implement deterministic project-filtered selection and explanations.
- [ ] Run focused selection tests and fast verification.
- [ ] Add and pass provider-neutral architecture tests.

## Review and verification

- [ ] Review the complete diff against the specification, plan, ADR, and modularity assessment.
- [ ] Run `git diff --check`.
- [ ] Run `pwsh -NoProfile -File scripts/change-workflow.ps1 check`.
- [ ] Run `pwsh -NoProfile -File scripts/verify.ps1`.
- [ ] Commit each logical P0 change unit without bypassing hooks.
- [ ] Record current closeout evidence and residual programme phases.

## Later phases

- [ ] Reconcile platform entry points after 047 merges.
- [ ] Implement read-only GitHub Project inventory and adapter contracts.
- [ ] Implement mutation workflows, review evidence, traceability, CLI, CI, and reconciliation in separate governed slices.
- [ ] Update reader-facing repository documentation at the configured integration milestone.
