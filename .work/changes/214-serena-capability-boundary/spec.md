# Change Specification: Serena Capability Boundary

- **Change ID**: `214-serena-capability-boundary`
- **Status**: Approved for implementation under issue #408
- **Complexity**: medium
- **Risk triggers**: `security`, `public_contract`

## Outcome

Make KIS expose exactly the approved Serena read-only semantic surface even when the upstream Serena MCP process advertises additional operations.

## Authority and scope

- Authoritative sources: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, issue #408, and current provider/capability contracts.
- Owned implementation: Serena adapter/provider projection only, plus focused provider/capability tests and this change record.
- This is structural provider-contract shaping, not a new HR-001/HR-002/HR-003 policy rule.
- Excluded: reviewer architecture (#403/#395), merge delta inspection (#407), Discover behavior, Work Management behavior, and policy changes.

## Requirements

- **REQ-001**: Public Serena operations are exactly `get_symbols_overview`, `find_symbol`, and `find_referencing_symbols`.
- **REQ-002**: Upstream-discovered Serena operations outside that set never enter KIS runtime-tool projection or normalized catalogue augmentation.
- **REQ-003**: Capability search and description cannot discover disallowed Serena operations.
- **REQ-004**: Generic KIS dispatch rejects disallowed Serena operations as unknown even if an upstream/direct callable with that name exists.
- **REQ-005**: Missing approved upstream tools remain unavailable/status-only rather than widening the surface or substituting another operation.

## Acceptance

1. Provider status, descriptor capability names, runtime projection, normalized catalogue, search, and dispatch agree on the same three-operation public surface.
2. Injected upstream mutation/admin/shell metadata is ignored rather than inferred into KIS capabilities.
3. `serena_delete_memory`, `serena_edit_memory`, `serena_execute_shell_command`, `serena_replace_symbol_body`, and `serena_write_memory` are neither discoverable nor generic-dispatchable.
4. Existing approved semantic reads remain available with their upstream invocation schemas when present.
5. Focused tests, governed scope validation, independent review, and exact-head canonical verification pass.

## Risks and recovery

- Risk: filtering the runtime-tool probe could accidentally suppress an approved read. Mitigation: exact positive assertions for all three names plus existing provider contract tests.
- Risk: upstream renames an approved operation. Expected behavior is fail-closed/status-only until explicitly reviewed.
- Recovery: revert the bounded Serena projection change; no data migration or provider-state mutation is required.
