# Tasks: Health Guard Recovery Hardening

- [x] Confirm authority and scope.
- [x] Forward against current `main` and identify stale merged startup-hook behavior.
- [x] Enforce 60-second grace, canonical listener PID ownership, one guard per generation, and generation-pinned recovery retries.
- [x] Add regression coverage for duplicate guards and stale retry generation loss.
- [x] Run `pwsh -File scripts/change-workflow.ps1 check`.
- [x] Run focused startup/recovery tests (59 passed).
- [ ] Run required review / publication verification and record closeout evidence.
- [ ] Merge and run safe cleanup from `main`.
