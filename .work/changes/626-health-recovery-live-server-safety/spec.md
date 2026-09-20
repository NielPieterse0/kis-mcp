# Change Specification: Health Recovery Live Server Safety

- **Change ID**: `626-health-recovery-live-server-safety`
- **Status**: Active
- **Work**: `WORK-660` / GitHub issue `#660`

## Outcome

Prevent tunnel/provider failure from replacing a live KIS server, detect stale OpenAI control-plane polling from the tunnel client's local telemetry, and recover only the owned tunnel when the local server remains healthy.

## Authority and scope

- Authoritative Work contract: `WORK-660` task handoff and issue acceptance criteria.
- Owned implementation: runtime health guard, independent recovery launcher, selected-instance launcher, and focused startup/health tests declared by `scope.json`.
- Existing once-through lifecycle is explicitly out of scope and must not gain repeated verification, review, PR, CI, merge, or closeout steps.

## Requirements

- **REQ-001**: Local KIS liveness is proven independently of tunnel/provider state.
- **REQ-002**: Tunnel process/readiness and control-plane poll freshness are separate health dimensions.
- **REQ-003**: A healthy local KIS server suppresses destructive full-runtime recovery.
- **REQ-004**: Persistently stale control-plane polling triggers tunnel-only recovery with run-ID and recovery-lock fencing.
- **REQ-005**: Local MCP liveness uses a real `2026-07-28` `server/discover` request; legacy initialize remains compatibility evidence only.
- **REQ-006**: Health evidence records local server, tunnel process, control-plane freshness, and the fact that external OpenAI reachability is not directly observable by this local guard.
- **REQ-007**: Mandatory tunnel-client version preflight uses explicit redirected process launch with bounded retry, so transient cold-boot/Windows native-process plumbing failures do not abort the whole startup.

## Acceptance

1. Given a responsive KIS listener and degraded/stale tunnel, full runtime recovery is never launched.
2. Given a responsive KIS listener and stale control-plane poll telemetry after grace, only the owned tunnel is recycled.
3. Given a dead local KIS listener after grace, existing generation-fenced full recovery remains available.
4. Control-plane freshness is derived from `commands_poll_last_successful_timestamp_seconds`, not `/readyz` alone.
5. The modern MCP health probe succeeds through `server/discover` with request-scoped 2026 metadata.
6. Focused regression tests pass without changing once-through workflow files.
7. Tunnel-client version validation distinguishes missing/hash/version mismatch from transient launch/probe failure and retries only within one bounded startup invocation.

## Risks and recovery

- Tunnel recycle can temporarily remove remote reachability; recovery is bounded to the exact current run and does not terminate the server.
- Missing/malformed control-plane telemetry is treated as degraded rather than healthy.
- Existing full-runtime recovery remains the fallback only when the local server itself is unresponsive.

## Out of scope

- Persistent MCP Tasks/job storage (`#498`).
- FastMCP version upgrade except as a separately governed follow-up.
- Changing Work/once-through lifecycle semantics.
