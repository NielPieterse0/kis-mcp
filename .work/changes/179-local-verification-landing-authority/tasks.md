# Tasks: Local Verification Landing Authority

- [x] Re-establish repository truth: change 174 merged and `main` synchronized at `b68da37a8269dd7c4e9523a3db0c5b9a279e1f11`.
- [x] Define the replacement landing authority and bounded exclusions.
- [x] Restore full-suite pytest collection with the minimal `tests/execution/__init__.py` package marker and project-management import-order correction discovered after the live runtime restart.
- [x] Add failing merge-readiness tests for exact-head local evidence and rejection cases.
- [x] Implement provider-neutral local exact-head merge readiness.
- [x] Replace Actions-dependent normal PR completion descriptors.
- [x] Retire Actions-backed speculative queue workflows from the canonical catalogue.
- [x] Reconcile `AGENTS.md`, `SPEC.md`, platform concept, and verification runbook.
- [x] Run focused tests and `pwsh -NoProfile -File scripts/change-workflow.ps1 check`.
- [x] Run full `pwsh -NoProfile -File scripts/verify.ps1` and `git diff --check`.
- [x] Complete required code-quality and architecture/public-contract reviews, using governed manual exact-diff fallback for architecture after specialist timeouts.
- [ ] Commit, prepare exact reviewable PR, locally verify exact reconciled PR head, merge, refresh `main`, and run safe cleanup.
