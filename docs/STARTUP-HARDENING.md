# Startup Hardening Record

## Status and authority

This file is supporting engineering history for the startup-hardening work. It is not a current operator runbook and must not redefine live startup, credential, tunnel, instance-ownership, or recovery behavior.

Current operator procedure is owned by [`OPERATIONS.md`](OPERATIONS.md). Current implemented architecture is owned by [`../SPEC.md`](../SPEC.md). Trust semantics remain owned by [`TRUST-MODEL.md`](TRUST-MODEL.md). When this record differs from those authorities, the current authorities win.

## Durable hardening outcomes

The startup work established the following constraints that remain relevant to implementation review:

- `kis-op` and `kis-dev` are separate supervised remote instances with distinct configured identities and loopback ports.
- Startup owns only the selected instance's server and tunnel processes; it must not terminate or reconfigure the peer instance.
- A selected listener may be reclaimed only when KIS can positively prove selected-instance ownership. Unrelated listeners fail with diagnostics.
- The local remote runtime is Streamable HTTP with checked-in stateless/JSON-response settings; KIS does not require a conversation-long MCP session.
- Startup and normal verification do not install or update dependencies from the network.
- Provider startup contains the pinned Desktop Commander automatic external-activity cases before ordinary Work invocation enforcement begins.
- Desktop Commander's provider-native command and directory restriction fields remain empty gateway invariants rather than a second policy boundary.
- Runtime diagnostics and generated state remain beneath the configured KIS state root and do not contain credential values.
- Replacement and recovery paths preserve prior state recoverably rather than permanently deleting it.

These statements summarize implementation properties only. Exact scripts, current credential indirection, vault/runtime-unlock behavior, readiness fields, error codes, tunnel setup, and commissioning commands belong exclusively to `OPERATIONS.md`.
