# Context7 and Serena Adapter Plan

## Phase 1 — Operator approval gate

- [x] Inspect repository authority, active claims, and the existing hard-block register.
- [x] Verify current official Context7 and Serena capabilities and candidate versions.
- [ ] Add only the new Serena HR mappings to `docs/HARD-BLOCK-APPROVAL-REGISTER.md`.
- [ ] Present the entries and reasons to the operator.
- [ ] Record operator decisions in the existing register.

Production implementation is blocked until the three new register entries are approved or amended.

## Phase 2 — Context7 adapter

- [ ] Write failing tests for descriptor metadata, settings validation, readiness containment, fixed endpoint identity, redacted credential handling, and the two upstream MCP operations.
- [ ] Implement independent Context7 settings, contracts, installer, adapter, descriptor, and readiness probe.
- [ ] Verify that Context7 uses `ToolBoundary.APPROVED_EXTERNAL_SERVICE` and does not enter the local Work command path.
- [ ] Verify failure does not prevent Serena or wider runtime startup.

## Phase 3 — Serena adapter

- [ ] Write failing tests for descriptor metadata, isolated provider state, upstream tool preservation, project-relative path resolution, shell-command effect delegation, and memory quarantine.
- [ ] Implement independent Serena settings, contracts, installer, stdio adapter, descriptor, readiness probe, and effect mapping.
- [ ] Implement only the operator-approved HR mappings from the existing register.
- [ ] Verify failure does not prevent Context7 or wider runtime startup.

## Phase 4 — Registration and verification

- [ ] Register both descriptors in the existing Tools service/runtime without coupling them to each other.
- [ ] Run focused adapter tests.
- [ ] Run change-governance validation and scope checks.
- [ ] Run full repository verification serially.
- [ ] Review the complete diff against AGENTS.md, the trust model, and the approved register decisions.
- [ ] Commit, push, and raise a reviewable PR without merging it.
