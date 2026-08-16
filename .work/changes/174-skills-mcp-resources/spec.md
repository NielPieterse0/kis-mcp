# Change Specification: Skills MCP Resources

- **Change ID**: `174-skills-mcp-resources`
- **Status**: Approved by operator direction
- **Risk Profile**: architecture boundary + public contract

## Outcome
Expose the validated canonical Skills snapshot through native read-only MCP resources without creating a second catalogue, mutation path, or execution authority.

## Authority and scope
- Canonical catalogue remains `C:\Projects\.agents\skills` through existing Skills validation/configuration.
- The existing immutable `SkillCatalogue` remains the sole resource-content source.
- Existing KIS-native Skills tools and mutations remain unchanged.

## Requirements
- **REQ-001**: `skill:///` exposes a bounded deterministic catalogue index with skill IDs, entrypoint URIs, snapshot identity, and entrypoint SHA-256.
- **REQ-002**: `skill:///<skill-id>/SKILL.md` returns exact canonical entrypoint bytes represented by the active snapshot.
- **REQ-003**: `skill:///<skill-id>/resource?path=<relative-path>` returns exact supporting-resource bytes, including nested resources.
- **REQ-004**: resource reads preserve traversal/link/reparse/collision/package/suffix/size validation and reject bytes that no longer match the active snapshot hash/size.
- **REQ-005**: scripts/assets/agents/references are resources/data only; resource exposure grants no execution authority.
- **REQ-006**: progressive disclosure is preserved: discovery exposes the index and templates, not every supporting file eagerly.
- **REQ-007**: existing native Skills behavior remains unchanged.
- **REQ-008**: the durable Skills module specification documents the resource contract and authority boundary.

## Acceptance
1. Text, nested, script, and binary fixtures read through MCP with byte-identical SHA-256.
2. Traversal and stale-byte attempts fail closed.
3. Passive resource discovery does not mutate the catalogue or execute resource content.
4. Focused Skills tests and governed change checks pass.

## Out of scope
Delivery-path telemetry, dual-delivery experiment routing, and catalogue-wide rollout remain #314–#316.