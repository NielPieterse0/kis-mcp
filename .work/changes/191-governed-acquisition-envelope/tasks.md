# Tasks: Governed Acquisition Envelope

- [x] Confirm all historical source files equal current reconstructed parent state.
- [x] Port only the acquisition/settings/tests payload from `141bbe8`.
- [x] Run focused tests and Ruff.
- [x] Run scope check.

## External exact-head close gate

- Freeze one immutable head, then run required reviews and GitHub Actions against that same head.
- Merge, align, close #361, and clean without a metadata-only follow-up commit.