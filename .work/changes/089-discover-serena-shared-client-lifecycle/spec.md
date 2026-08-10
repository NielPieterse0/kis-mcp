# Change Specification: Discover Serena Shared Client Lifecycle

- **Change ID**: `089-discover-serena-shared-client-lifecycle`
- **Status**: Approved by current commissioning request
- **Risk Profile**: standard

## Outcome

Keep Serena's shared runtime client published across nested FastMCP proxy contexts so live Discover can use the already-running Serena provider instead of degrading to deterministic fallback.

## Authority and scope

- Authoritative sources: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/OPERATIONS.md`.
- Owned implementation: `src/kis_mcp/providers/serena/adapter.py`.
- Owned regression: `tests/providers/test_context7_serena_providers.py`.
- Excluded: policy rules, provider versions/settings, Discover persistence contracts, direct Serena exposure.
- Base/integration target: `main`.

## Requirements

- **REQ-001**: Nested enters of `_SharedProviderClient` MUST keep the outer active client and event loop published until the outermost exit.
- **REQ-002**: The final outer exit MUST clear the published client and loop exactly as before.
- **REQ-003**: Serena provider startup, tool discovery, offline enforcement, and central project-state behavior MUST remain unchanged.
- **REQ-004**: Live `inspect_project` refresh on registered `kis-mcp` MUST no longer report `SEMANTIC_PROVIDER_UNAVAILABLE` when Serena is ready.

## Acceptance

1. A regression demonstrates current nested context exit clears the active client while the outer context is still open.
2. After the fix, that regression passes and the client remains usable until outer exit.
3. Focused Serena/provider tests and canonical `scripts\verify.ps1` pass on the integrated change.
4. Fresh live `kis-dev` commissioning shows Serena ready, central state only, and Discover semantic enrichment no longer failing independently.

## Risks and recovery

- Risk: incorrect nesting accounting could retain a stale client after shutdown or clear it too early during concurrent proxy calls.
- Mitigation: count active contexts and assert both inner-exit retention and final-exit clearing.
- Recovery: revert the bounded 089 commit; deterministic Discover fallback remains available.

## Out of scope

- Expanding Serena's public tool exposure.
- Changing the three-rule policy or provider authentication.
- Unrelated provider-status wording cleanup.
