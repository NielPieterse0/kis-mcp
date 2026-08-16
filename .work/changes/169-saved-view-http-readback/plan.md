# Saved View HTTP Readback Implementation Plan

**Goal:** Restore all-12 behavioral readiness after the canonical backlog expanded broad active views.

**Architecture:** Keep the existing REST saved-view endpoint and bounded manual pagination. Extend only the response-page decoder so a body-only JSON list is accepted when its item count proves there cannot be a next page; otherwise remain unverified.

**Tech stack:** Python 3.13, pytest, existing `gh api` registered-Project commissioner path.

## Constraints

- Stay inside `scope.json`.
- Test first and observe the intended failure before production code.
- Do not alter canonical filters, view mutation behavior, authentication, or policy.
- Preserve every existing fail-closed pagination and field-shape check.

## Tasks

1. Add regression coverage for a short body-only saved-view page and for a page at the 100-item completeness boundary.
2. Run the focused tests and record the red failure.
3. Implement the smallest page-decoder change, passing the configured page bound explicitly.
4. Run focused provider tests, affected Work Management tests, Ruff/compile, `git diff --check`, and governed scope check.
5. Review code quality and API contracts on the exact immutable source; resolve findings and rerun evidence.
6. Publish an exact reviewed head, require provider-native exact-head CI, merge, restart `kis-dev`, and recommission all 12 views.
7. Require zero legacy `Todo`/`In Progress`, zero view drift/unverified, empty schema plan, then close #304 and reconcile Work Management.