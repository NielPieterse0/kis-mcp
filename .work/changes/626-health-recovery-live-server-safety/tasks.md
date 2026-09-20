# Tasks: Health Recovery Live Server Safety

- [x] Reconcile `#660` into Work, claim it, and bind this existing governed change.
- [x] Confirm the live tunnel exposes control-plane poll freshness locally.
- [ ] Add modern MCP 2026 local-server probe.
- [ ] Add explicit tunnel process/control-plane/remote-observability health evidence.
- [ ] Add exact-run tunnel-only recovery without terminating the KIS server.
- [ ] Add focused regression coverage for stale polling and tunnel-only recovery.
- [x] Harden tunnel-client version preflight for cold-boot transient native-process failures with explicit redirection and bounded retry.
- [x] Add focused tunnel preflight regression assertions.
- [ ] Run `pwsh -File scripts/change-workflow.ps1 check` and focused verification.
- [ ] Execute the existing verification/review path once; do not duplicate it.
- [ ] Prepare PR, exact-head CI, merge, documentation reconciliation, and cleanup through the existing lifecycle.
