# Closeout: Repository-Scoped Work Projection

## Implemented scope

Repository-bound shared-Project reads now filter by registered repository while preserving unbound portfolio reads, and explicit mismatched repository reconciliation fails before provider I/O.

## Validation

Focused provider/project tests: 27 passed. Ruff passed on all touched production/test files. Scope check passed. Canonical repository verification is GitHub Actions on the frozen PR head.

## Landing

Issue #360. Reviews and GitHub Actions bind to one immutable candidate head; merge/cleanup remains external exact-head state.

