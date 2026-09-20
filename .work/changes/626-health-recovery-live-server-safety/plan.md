# Health Recovery Live Server Safety Implementation Plan

**Goal:** Isolate local KIS liveness from tunnel health and repair stale control-plane polling by recycling only the exact owned tunnel.

**Architecture:** The health guard reads only local evidence: current generation ownership, the loopback MCP endpoint, the tunnel admin endpoint, and tunnel Prometheus metrics. A modern `server/discover` request proves KIS liveness. `/readyz` proves tunnel-local readiness, while `commands_poll_last_successful_timestamp_seconds` proves recent control-plane polling. If KIS is healthy but polling stays stale through grace, the existing independent recovery surface runs in tunnel-only mode. Full runtime recovery remains reserved for a locally unresponsive KIS server.

**Tech Stack:** PowerShell 7, tunnel-client local admin/metrics HTTP, MCP 2026 JSON-RPC, pytest.

## Global constraints

- Stay inside `scope.json`.
- Add regression assertions before changing recovery behavior.
- Preserve run-ID fencing, single recovery lock, and bounded grace/backoff.
- Never restart `kis-op` while implementing this change.
- Do not add or repeat any once-through lifecycle step.

### Task 1: Prove modern/local health evidence

- [ ] Add modern `2026-07-28` `server/discover` health probing.
- [ ] Parse tunnel control-plane poll freshness from local `/metrics`.
- [ ] Persist bounded health evidence without claiming unobserved external reachability.

### Task 2: Add tunnel-only recovery

- [ ] Add exact-run tunnel-only mode to `recover-chatgpt.ps1`.
- [ ] Stop only the recorded tunnel PID and start the configured tunnel against the existing healthy KIS endpoint.
- [ ] Atomically update the current generation with the replacement tunnel PID.
- [ ] Keep full runtime recovery unchanged for local-server failure.

### Task 3: Harden cold-boot tunnel-client preflight

- [x] Replace implicit PowerShell native `--version` capture with explicit `ProcessStartInfo` stdout/stderr redirection.
- [x] Add a bounded three-attempt retry for transient launch/probe failures while preserving hash/version fail-closed checks.
- [x] Add focused regression assertions for the explicit process boundary and failure taxonomy.

### Task 4: Verify and close

- [ ] Run focused health/startup tests and change-governance check.
- [ ] Execute the existing KIS change verification/review once.
- [ ] Prepare PR, exact-head CI, merge, and cleanup through the existing workflow only.