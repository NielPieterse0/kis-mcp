# Change Specification: SEP-2640 Skills Extension

- **Change ID**: `611-sep2640-skills-extension`
- **Status**: Implemented pending publication
- **Complexity**: Large
- **Risk triggers**: architecture boundary, public contract, security

## Outcome

Implement issue #569 by adding the draft SEP-2640 Skills-over-MCP extension over the existing KIS Skills catalogue without creating a second catalogue, execution path, trust rule, or `once_through` dependency.

## Authority and scope

- Authorities: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/SKILLS-MODULE-PRODUCT-SPEC.md`, SEP-2640 upstream proposal.
- Owned: `src/kis_mcp/skills/**`, `tests/skills/**`, `docs/SKILLS-MODULE-PRODUCT-SPEC.md`, this change record.
- Shared: `SPEC.md` (no edit required for this slice).
- Excluded: `src/kis_mcp/workflows/once_through/**`.

## Requirements

- **REQ-001**: Advertise `io.modelcontextprotocol/skills` through FastMCP extension capabilities.
- **REQ-002**: Serve negotiated `skills/list` and URI-keyed `skills/get` with complete per-file SHA-256/size manifests.
- **REQ-003**: Serve canonical direct `skill:///` resources from the immutable validated catalogue; optional directory reads return direct children only.
- **REQ-004**: Fail closed on snapshot drift, unlisted resources, digest/size mismatch, and frontmatter mismatch.
- **REQ-005**: Bind persisted approval identity to the complete advertised resource set so content changes require reapproval.

## Acceptance

1. A client negotiating the extension can list and get Skills using the current snapshot and receives deterministic integrity metadata.
2. A client that does not negotiate the extension cannot invoke its methods.
3. Supporting files are individually addressable and snapshot-verified; archive delivery is not introduced.
4. Existing KIS-native Skills tools, Work mutation routing, telemetry, and the three-rule trust boundary remain intact.
5. Focused Skills tests and governed scope validation pass on the final implementation state.

## Risks and recovery

- Draft upstream contract may still change; the implementation declares its draft baseline and remains isolated in `skills.sep2640`.
- Incorrect manifest handling could create TOCTOU or approval drift; complete manifests plus host verification helpers fail closed.
- Recovery is branch/worktree rollback before merge; after merge use the repository's normal governed recovery path.

## Out of scope

- Archives, automatic skill execution, network distribution, new Work policy rules, `once_through` changes, or unrelated Skills lifecycle redesign.
