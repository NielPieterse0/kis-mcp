# Change Specification: Startup Runtime Reclaim

- **Change ID**: `082-startup-runtime-reclaim`
- **Status**: Active
- **Risk Profile**: standard
- **Development Level**: Medium

## Outcome

Starting a selected ChatGPT instance must safely reclaim an already-running selected `kis-mcp` server, force-stop its owned process tree, verify the configured port is released, and only then launch the replacement.

## Authority and scope

- Authoritative sources: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/OPERATIONS.md`.
- Owned paths: `scripts/startup-instance-lifecycle.ps1`, `tests/test_startup_scripts.py`, `docs/OPERATIONS.md`, change metadata.
- Shared paths: none.
- Excluded paths: policy, runtime provider implementation, settings, peer-instance lifecycle.
- Dependencies: existing PowerShell startup lifecycle and Windows process metadata only.
- Integration owner: none.

## Requirements

- **REQ-001**: Treat the selected runtime as owned when its command line proves it was launched through the canonical project Python path for `kis_mcp.remote_runtime --instance <selected>`, even if Windows resolves `ExecutablePath` to the underlying base interpreter.
- **REQ-002**: Continue refusing to stop a listener that cannot be positively identified as the selected KIS runtime.
- **REQ-003**: For a positively identified selected runtime, retain forceful process-tree termination and wait until the selected port is no longer listening before replacement startup proceeds.
- **REQ-004**: Do not inspect, stop, or otherwise disturb the peer KIS instance.
- **REQ-005**: Document the selected-instance reclaim behavior and unrelated-process refusal accurately.

## Acceptance

1. Given a selected KIS process whose `ExecutablePath` is the base interpreter but whose command line begins with the canonical project Python launcher and selected remote-runtime invocation, the identity check accepts it.
2. Given an unrelated process on the selected port, startup still raises `KIS_MCP_PORT_OWNED_BY_OTHER_PROCESS` and does not stop it.
3. Given an accepted stale selected runtime, startup force-stops its owned process tree and `Wait-KisMcpSelectedPortReleased` gates replacement startup.
4. Focused startup tests and canonical repository verification pass on the final change.

## Risks and recovery

- Risk: an over-broad identity matcher could terminate an unrelated process. Mitigation: require both canonical Python launch evidence and exact selected module/instance arguments.
- Recovery: revert the bounded change; startup then returns to refusing ambiguous port owners rather than force-stopping them.

## Out of scope

- Killing arbitrary processes by port or executable name.
- Changing KIS policy, provider authentication, tunnel credentials, or peer-instance behavior.
- Adding a separate stop command or permanent process manager.
