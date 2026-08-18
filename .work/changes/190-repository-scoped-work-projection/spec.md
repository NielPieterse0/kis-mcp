# Change Specification: Repository-Scoped Work Projection

## Requirements

1. A repository-bound Project inventory excludes foreign repository items.
2. Pagination continues across foreign records until the matching-item limit or upstream end is reached.
3. A truncated result means the repository-scoped matching result may still be incomplete, not merely that foreign records existed.
4. Reconciliation for a bound project rejects explicit foreign source repositories before idempotency/provider mutation.
5. Unbound Project bindings retain intentional portfolio-wide visibility.

## Acceptance

Focused adapter and GitHub project-management tests pass; Ruff and scope check pass; code-quality/API-contract review and GitHub Actions pass on one frozen head.
