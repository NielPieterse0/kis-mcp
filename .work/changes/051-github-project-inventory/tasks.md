# Tasks: GitHub Project Inventory

## Governance

- [x] Create stacked branch and isolated worktree from change 049.
- [x] Register exact owned, shared, excluded, and dependency paths before implementation.
- [x] Validate the stacked claims and worktree.
- [x] Set programme P1 state to active.

## Provider-neutral contracts

- [ ] Write failing backend contract tests.
- [ ] Implement immutable inventory contracts and backend protocol.
- [ ] Update shared exports and architecture tests.
- [ ] Run focused tests and repository verification.

## GitHub adapter

- [ ] Write failing fixed-call, normalization, pagination, truncation, and error tests.
- [ ] Implement the read-only GitHub Project adapter.
- [ ] Prove no mutation tool can be invoked.
- [ ] Run focused tests and repository verification.

## Provider metadata

- [ ] Write failing descriptor and capability-contribution tests.
- [ ] Advertise exact Project read operations.
- [ ] Run focused tests and full verification.

## Review and closeout

- [ ] Complete findings-first review and regression fixes.
- [ ] Run `git diff --check` and change-governance checks.
- [ ] Run `pwsh -NoProfile -File scripts/verify.ps1`.
- [ ] Record P1 completion and residual phases without claiming live commissioning.
