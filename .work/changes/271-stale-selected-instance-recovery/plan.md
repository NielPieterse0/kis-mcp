# Stale Selected-Instance Recovery Plan

**Goal:** Complete #600 live recovery acceptance without weakening unrelated-port ownership checks.

- [x] Reproduce stale selected listener rejection.
- [x] Separate selected-instance identity from canonical interpreter provenance.
- [x] Use identity-only matching for preflight reclamation.
- [x] Keep canonical provenance validation for newly launched runtime ownership.
- [x] Add regression coverage for noncanonical selected-instance identity.
- [ ] Verify, review, publish, exact-head CI, merge, and live recovery acceptance.