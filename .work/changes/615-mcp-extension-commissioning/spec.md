# Change Specification: MCP Extension Commissioning

- **Change ID**: `615-mcp-extension-commissioning`
- **Status**: Active
- **Complexity**: Large
- **Risk triggers**: architecture boundary, persistent state, public contract

## Outcome

Add a reusable in-process live MCP-extension commissioning operation, with SEP-2640 Skills as the first profile, and strengthen Skills telemetry so protocol negotiation, exact runtime/source identity, integrity evidence, delivery path, and downstream outcomes remain bounded and correlatable.

## Authority and scope

- Authority: `AGENTS.md`, issue #621, current Skills module product specification, existing SEP-2640 contracts/tests.
- Owned implementation: `src/kis_mcp/mcp_extensions/**`, `src/kis_mcp/skills/**`.
- Owned tests: `tests/mcp_extensions/**`, `tests/skills/**`.
- Durable documentation owner: `docs/SKILLS-MODULE-PRODUCT-SPEC.md`.
- Explicitly excluded: generic post-merge observer code under `commissioning/**` and `commissioning_runtime/**` (issue #620).
- No localhost or outbound network path may be introduced.
- HR-001, HR-002, and HR-003 remain unchanged.

## Requirements

- **REQ-001**: `commission_mcp_extension` must traverse the real FastMCP dispatcher using an in-process client transport.
- **REQ-002**: receipts bind runtime instance, server identity fingerprint, source revision, protocol version, extension ID/settings/profile, timestamp, method outcomes, and overall result.
- **REQ-003**: receipt matching fails closed across runtime, source, protocol, extension, settings, or profile drift.
- **REQ-004**: the SEP-2640 profile must exercise negotiated `skills/list`, `skills/get`, `resources/read`, optional `resources/directory/read`, integrity/frontmatter verification, and an unnegotiated `METHOD_NOT_FOUND` control.
- **REQ-005**: Skills telemetry must distinguish extension discovery/list/get/directory observation from actual entrypoint/resource loads and caller-reported application outcomes.
- **REQ-006**: MCP telemetry must retain stable server/runtime fingerprint, negotiated protocol/extension settings, canonical skill identity, commissioning receipt correlation, and ordinary-vs-commissioned integrity provenance without retaining request content.
- **REQ-007**: existing SQLite telemetry stores migrate additively; existing `kis_native` rows and reports remain valid.
- **REQ-008**: telemetry persistence remains observational and cannot overturn a valid protocol response.
- **REQ-009**: delivery comparison must keep exact package-hash/path attribution and expose commissioned versus uncommissioned MCP evidence rather than pooling it opaquely.
- **REQ-010**: bounded readiness must distinguish catalogue readiness, extension registration, and last matching live commissioning evidence.

## Acceptance

1. A current in-process runtime can commission the registered Skills extension without network access.
2. Positive SEP-2640 steps and the negative unnegotiated control traverse the real request dispatcher and return bounded method evidence.
3. Advertised resource digest/size and SKILL.md frontmatter are proven by the commissioning run.
4. Stale receipt matching returns false after any bound identity change.
5. Real protocol calls create semantically distinct Skills telemetry with matching commissioning identity.
6. Reported outcomes still require an exact prior observed load on the selected delivery path and canonical skill identity.
7. Privacy/redaction, bounded retention, migration, and telemetry-failure behavior remain intact.
8. Focused protocol/telemetry/identity/privacy/migration tests and canonical exact-head CI pass.
9. Post-merge `kis-dev` commissioning produces live PASS evidence suitable for retrospective attachment to #569.

## Risks and recovery

- Protocol/API mismatch: fail closed with typed method evidence; no direct-function fallback.
- Persistent telemetry migration: additive columns only; rollback is code rollback while prior rows remain readable.
- Runtime/source drift: invalidate matching rather than reuse stale evidence.
- Recovery: revert the bounded change; no generated commissioning state is repository authority.

## Out of scope

- Generic post-merge observer behavior (#620).
- Reopening or modifying #569 implementation scope.
- Network/localhost bypasses, automatic skill script execution, or new Work policy rules.
