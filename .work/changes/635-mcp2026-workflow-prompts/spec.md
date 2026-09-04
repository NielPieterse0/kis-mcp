# Change Specification: MCP 2026 Workflow Prompts

- **Change ID**: `635-mcp2026-workflow-prompts`
- **Status**: Active
- **Complexity**: Medium
- **Risk triggers**: `architecture_boundary`, `public_contract`

## Outcome

Complete #589 without creating a second workflow authority: add thin MCP workflow prompts, make discovery list identity deterministic, and resolve cache/header-routing residuals from current MCP 2026 evidence.

## Authority and scope

- Authority: `AGENTS.md`, applicable MCP boundary in `SPEC.md`, issue #589, current pinned FastMCP/MCP contracts.
- Owned code: `src/kis_mcp/mcp2026_prompts.py`, `src/kis_mcp/gateway/composition.py`.
- Owned tests: `tests/test_mcp2026_wire.py`.
- Change records: `.work/changes/635-mcp2026-workflow-prompts/**`.
- Excluded: `src/kis_mcp/mcp2026.py` and `SPEC.md`, currently claimed by change #628.

## Requirements

- **REQ-001**: Register `start-change`, `resume-change`, `take-next-work`, and `explain-change` as thin user-invoked MCP prompts that delegate authority to existing KIS Work/change operations.
- **REQ-002**: Return tools, prompts, resources, and resource templates in stable deterministic identity order.
- **REQ-003**: Do not enable positive list/read caching unless current runtime behavior can guarantee stale identity is not served after capability/catalogue changes.
- **REQ-004**: Adopt custom `Mcp-Method` / `Mcp-Name` routing only if it adds material routing value without duplicating transport validation or policy authority.

## Architecture decisions

### AD-001 — Positive cache TTL deferred

The pinned repository runtime is FastMCP 4.0.0b3 with MCP 2026-07-28 cacheable list-result fields. FastMCP's `cache_ttl` applies one positive TTL uniformly to every cacheable method. KIS discovery includes dynamic provider/skill/capability state, so a uniform positive TTL can outlive a catalogue/runtime fingerprint change. This change therefore emits no positive TTL and instead stabilizes list ordering. Cache enablement requires a future invalidation/fingerprint contract; absence of a cache hint cannot serve stale cached identity.

### AD-002 — No custom KIS header router

The pinned MCP SDK already implements and validates `Mcp-Method` / `Mcp-Name` transport headers against request identity. The current KIS gateway is not a method/name-based multi-upstream HTTP router; provider composition happens behind one governed FastMCP boundary. Adding a KIS header router would duplicate protocol validation without material routing benefit and could become an unintended authority/policy layer. The headers remain transport metadata, not Work authority.

## Acceptance

1. All four prompts are discoverable and explicitly state that Work Management remains authoritative.
2. Discovery ordering is deterministic for prompts, tools, resources, and resource templates.
3. Tests prove the pinned SDK exposes MCP 2026 cacheable-result fields while KIS configures no positive cache TTL in this change.
4. Header routing is explicitly rejected by AD-002 with current-runtime evidence.
5. Focused tests, scope validation, change verification, required specialist reviews, and live candidate verification pass.

## Risks and recovery

- Risk: deterministic sorting could alter previous provider registration order. Mitigation: identity ordering is protocol-facing only and component lookup remains unchanged.
- Recovery: revert the change commit; no persistent migration or external state schema is introduced.

## Out of scope

- Custom transport/gateway header routing.
- Positive MCP cache TTL or a new cache store.
- Changes to Work lifecycle authority, Roots, Sampling, Logging, or `mcp2026.py`.
